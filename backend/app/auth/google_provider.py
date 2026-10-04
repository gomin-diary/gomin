"""Google OIDC provider; credentials and tokens never enter public errors."""
import asyncio
import hmac
import time
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

import httpx
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.errors import AppError
from app.schemas.signup import EmailInput


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str | None


def unavailable():
    return AppError(503, 'OAUTH_NOT_CONFIGURED', 'Google 로그인을 준비하고 있어요.')


class GoogleProvider:
    def __init__(self, http: httpx.AsyncClient, settings):
        self.http, self.settings = http, settings
        self.keys: dict = {}
        self.expires = 0.0
        self.lock = asyncio.Lock()
        self.last_unknown_refresh = 0.0

    def validate_config(self):
        s = self.settings
        if not s.google_oauth_client_id or not s.google_oauth_client_secret.get_secret_value():
            raise unavailable()
        for url, origin in [(s.google_oauth_redirect_uri, False), (s.auth_frontend_origin, True)]:
            try:
                p = urlsplit(url)
                _ = p.port
                local = p.hostname in ('localhost', '127.0.0.1', '::1')
                if not p.hostname or p.username or p.password or p.query or p.fragment:
                    raise ValueError()
                if p.scheme != 'https' and not (p.scheme == 'http' and local and not s.auth_cookie_secure):
                    raise ValueError()
                if origin and p.path not in ('', '/'):
                    raise ValueError()
                if not origin and p.path != '/api/v1/auth/google/callback':
                    raise ValueError()
            except ValueError:
                raise unavailable() from None
        try:
            Fernet(s.auth_oauth_encryption_key.get_secret_value().encode())
        except (ValueError, TypeError):
            raise unavailable() from None

    def encrypt_verifier(self, value: str) -> str:
        self.validate_config()
        return Fernet(self.settings.auth_oauth_encryption_key.get_secret_value().encode()).encrypt(value.encode()).decode()

    def decrypt_verifier(self, value: str) -> str:
        try:
            return Fernet(self.settings.auth_oauth_encryption_key.get_secret_value().encode()).decrypt(value.encode()).decode()
        except (ValueError, InvalidToken, UnicodeError):
            raise AppError(400, 'OAUTH_REQUEST_INVALID', 'Google 로그인을 다시 시작해 주세요.') from None

    def authorization_url(self, state: str, nonce: str, challenge: str) -> str:
        self.validate_config()
        return 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
            'client_id': self.settings.google_oauth_client_id, 'redirect_uri': self.settings.google_oauth_redirect_uri,
            'response_type': 'code', 'scope': 'openid email profile', 'state': state, 'nonce': nonce,
            'code_challenge': challenge, 'code_challenge_method': 'S256', 'prompt': 'select_account',
        })

    async def _load_keys(self):
        result = await self.http.get('https://www.googleapis.com/oauth2/v3/certs', timeout=10)
        result.raise_for_status()
        body = result.json()
        if not isinstance(body, dict) or not isinstance(body.get('keys'), list):
            raise ValueError()
        keys = {k['kid']: k for k in body['keys'] if isinstance(k, dict) and isinstance(k.get('kid'), str)
                and k.get('kty') == 'RSA' and k.get('use', 'sig') == 'sig' and k.get('alg', 'RS256') == 'RS256'}
        if not keys:
            raise ValueError()
        self.keys = keys
        self.expires = time.monotonic() + 3600

    async def exchange_and_verify(self, code: str, verifier: str, nonce: str) -> GoogleIdentity:
        self.validate_config()
        try:
            result = await self.http.post('https://oauth2.googleapis.com/token', data={
                'code': code, 'client_id': self.settings.google_oauth_client_id,
                'client_secret': self.settings.google_oauth_client_secret.get_secret_value(),
                'redirect_uri': self.settings.google_oauth_redirect_uri, 'grant_type': 'authorization_code',
                'code_verifier': verifier,
            }, timeout=10)
            result.raise_for_status()
            token = result.json()['id_token']
            if not isinstance(token, str) or len(token) > 16384:
                raise ValueError()
            header = jwt.get_unverified_header(token)
            if header.get('alg') != 'RS256' or not isinstance(header.get('kid'), str):
                raise ValueError()
            async with self.lock:
                if time.monotonic() >= self.expires:
                    await self._load_keys()
                if header['kid'] not in self.keys and time.monotonic() - self.last_unknown_refresh > 60:
                    await self._load_keys()
                    self.last_unknown_refresh = time.monotonic()
                key = jwt.PyJWK.from_dict(self.keys[header['kid']], algorithm='RS256').key
            claims = jwt.decode(token, key, algorithms=['RS256'], audience=self.settings.google_oauth_client_id,
                                issuer=['https://accounts.google.com', 'accounts.google.com'],
                                options={'require': ['exp', 'iat', 'iss', 'aud', 'sub', 'nonce', 'email', 'email_verified']})
            if claims['aud'] != self.settings.google_oauth_client_id or claims.get('azp', claims['aud']) != self.settings.google_oauth_client_id:
                raise ValueError()
            if not isinstance(claims['nonce'], str) or not hmac.compare_digest(claims['nonce'], nonce):
                raise ValueError()
            if claims['email_verified'] is not True or not isinstance(claims['sub'], str) or not 1 <= len(claims['sub']) <= 255:
                raise ValueError()
            email = EmailInput(email=claims['email']).email
            name = claims.get('name')
            return GoogleIdentity(claims['sub'], email, name if isinstance(name, str) else None)
        except (httpx.HTTPError, jwt.PyJWTError, ValueError, KeyError, TypeError):
            raise AppError(400, 'OAUTH_FAILED', 'Google 인증에 실패했어요. 다시 시도해 주세요.') from None
