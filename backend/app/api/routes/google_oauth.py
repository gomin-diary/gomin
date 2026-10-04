"""Google callback authenticates; the frontend owns navigation."""
import base64
import hashlib
import hmac
import re
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from supabase import AsyncClient

from app.auth.google_provider import GoogleProvider
from app.auth.oauth_repository import OAuthRepository
from app.auth.security import new_session_token, token_digest
from app.auth.session import get_auth_settings, set_session_cookie
from app.core.config import Settings
from app.core.errors import AppError
from app.db.client import get_supabase
from app.schemas.auth import MemberData
from app.schemas.google_oauth import GoogleSignupInput, CancelInput, PendingData, StartData
from app.schemas.response import ApiSuccess

router = APIRouter(prefix='/api/v1/auth/google', tags=['google-oauth'])
BINDING = 'gomin_oauth_browser'
PROOF = 'gomin_oauth_proof'
COOKIE_PATH = '/api/v1/auth/google'
Config = Annotated[Settings, Depends(get_auth_settings)]


def get_oauth_repository(db: Annotated[AsyncClient, Depends(get_supabase)]):
    return OAuthRepository(db)


def get_google_provider(request: Request, settings: Config):
    return request.app.state.google_provider

Repo = Annotated[OAuthRepository, Depends(get_oauth_repository)]
Provider = Annotated[GoogleProvider, Depends(get_google_provider)]


def cookie_token(request: Request, name: str):
    value = request.cookies.get(name, '')
    return value if re.fullmatch(r'[A-Za-z0-9_-]{43}', value) else None


def temporary_cookie(response: Response, name: str, token: str, settings: Settings):
    response.set_cookie(name, token, max_age=1800, httponly=True, secure=settings.auth_cookie_secure,
                        samesite='lax', path=COOKIE_PATH)
    response.headers['Cache-Control'] = 'no-store'


def clear_proof(response: Response, settings: Settings):
    response.delete_cookie(PROOF, path=COOKIE_PATH, secure=settings.auth_cookie_secure, httponly=True, samesite='lax')
    response.headers['Cache-Control'] = 'no-store'


def csrf_token(proof: str, settings: Settings):
    return hmac.new(settings.auth_oauth_encryption_key.get_secret_value().encode(),
                    ('oauth-signup:' + proof).encode(), hashlib.sha256).hexdigest()


def pending_tokens(request: Request):
    proof, binding = cookie_token(request, PROOF), cookie_token(request, BINDING)
    if not proof or not binding:
        raise AppError(400, 'OAUTH_PROOF_INVALID', 'Google 로그인을 다시 시작해 주세요.')
    return proof, binding


def mutation_tokens(request: Request, csrf: str, settings: Settings):
    proof, binding = pending_tokens(request)
    if request.headers.get('origin') != settings.auth_frontend_origin.rstrip('/') or not hmac.compare_digest(csrf, csrf_token(proof, settings)):
        raise AppError(403, 'FORBIDDEN', '인증 요청을 확인한 뒤 다시 시도해 주세요.')
    return proof, binding


def result_redirect(settings: Settings, result: str, code: str | None = None):
    params = {'result': result}
    if code:
        params['error'] = code
    response = RedirectResponse(settings.auth_frontend_origin.rstrip('/') + '/auth/google/result?' + urlencode(params), status_code=302)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@router.get('/start', response_model=ApiSuccess[StartData])
async def start(request: Request, repo: Repo, provider: Provider, settings: Config):
    provider.validate_config()
    if settings.auth_frontend_origin.rstrip('/') not in settings.cors_origins:
        raise AppError(503, 'OAUTH_NOT_CONFIGURED', 'Google 로그인을 준비하고 있어요.')
    state, nonce, verifier = new_session_token(), new_session_token(), new_session_token()
    binding = cookie_token(request, BINDING) or new_session_token()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    await repo.call('cleanup', {})
    await repo.call('begin', {'p_state': token_digest(state), 'p_binding': token_digest(binding),
                            'p_nonce': nonce, 'p_verifier': provider.encrypt_verifier(verifier)})
    authorization_url = provider.authorization_url(state, nonce, challenge)
    if request.query_params.get('response') == 'json':
        response = JSONResponse(ApiSuccess(data=StartData(authorization_url=authorization_url)).model_dump(mode='json'))
    else:
        response = RedirectResponse(authorization_url, status_code=302)
    temporary_cookie(response, BINDING, binding, settings)
    clear_proof(response, settings)
    return response


@router.get('/callback')
async def callback(request: Request, repo: Repo, provider: Provider, settings: Config):
    query = request.query_params
    # Uvicorn logs this shared scope when sending the response.
    request.scope['query_string'] = b''
    provider.validate_config()
    try:
        state, binding = query.get('state', ''), cookie_token(request, BINDING)
        if not binding or not re.fullmatch(r'[A-Za-z0-9_-]{43}', state):
            raise AppError(400, 'OAUTH_REQUEST_INVALID', 'Google 로그인을 다시 시작해 주세요.')
        row = await repo.call('consume', {'p_state': token_digest(state), 'p_binding': token_digest(binding)})
        if error := query.get('error'):
            return result_redirect(settings, 'cancelled' if error == 'access_denied' else 'error',
                                   None if error == 'access_denied' else 'OAUTH_FAILED')
        code = query.get('code', '')
        if not code or len(code) > 4096:
            raise AppError(400, 'OAUTH_FAILED', 'Google 인증에 실패했어요.')
        identity = await provider.exchange_and_verify(code, provider.decrypt_verifier(row['verifier']), row['nonce'])
        token, proof = new_session_token(), new_session_token()
        member = await repo.call('complete', {'p_state': token_digest(state), 'p_binding': token_digest(binding),
                                            'p_subject': identity.subject, 'p_email': identity.email, 'p_name': identity.name,
                                            'p_session': token_digest(token), 'p_proof': token_digest(proof)})
        if not member.get('new_member'):
            response = result_redirect(settings, 'login')
            set_session_cookie(response, token, settings)
            clear_proof(response, settings)
            return response
        response = result_redirect(settings, 'signup')
        temporary_cookie(response, PROOF, proof, settings)
        temporary_cookie(response, BINDING, binding, settings)
        return response
    except AppError as error:
        return result_redirect(settings, 'error', error.code)


@router.get('/pending', response_model=ApiSuccess[PendingData])
async def pending(request: Request, response: Response, repo: Repo, settings: Config):
    proof, binding = pending_tokens(request)
    row = await repo.call('pending', {'p_proof': token_digest(proof), 'p_binding': token_digest(binding)})
    response.headers['Cache-Control'] = 'no-store'
    return ApiSuccess(data=PendingData(**row, csrf_token=csrf_token(proof, settings)))


@router.post('/signup', response_model=ApiSuccess[MemberData], status_code=201)
async def signup(payload: GoogleSignupInput, request: Request, response: Response, repo: Repo, settings: Config):
    proof, binding = mutation_tokens(request, payload.csrf_token.get_secret_value(), settings)
    versions = {c.type: c.version for c in payload.consents}
    token = new_session_token()
    row = await repo.call('signup', {'p_proof': token_digest(proof), 'p_binding': token_digest(binding),
                                  'p_name': payload.name, 'p_session': token_digest(token),
                                  'p_terms': versions['terms_of_service'], 'p_privacy': versions['privacy_collection'],
                                  'p_expected_terms': settings.auth_terms_version, 'p_expected_privacy': settings.auth_privacy_version})
    set_session_cookie(response, token, settings)
    clear_proof(response, settings)
    return ApiSuccess(data=MemberData(**row))


@router.post('/cancel', response_model=ApiSuccess[None])
async def cancel(payload: CancelInput, request: Request, response: Response, repo: Repo, settings: Config):
    proof, binding = mutation_tokens(request, payload.csrf_token.get_secret_value(), settings)
    await repo.call('cancel', {'p_proof': token_digest(proof), 'p_binding': token_digest(binding)})
    clear_proof(response, settings)
    return ApiSuccess(data=None)
