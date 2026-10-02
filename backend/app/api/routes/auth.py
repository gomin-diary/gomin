import re
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool
from supabase import AsyncClient

from app.auth.repository import AuthRepository
from app.auth.security import DUMMY_PASSWORD_HASH, new_session_token, token_digest, verify_password
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.client import get_supabase
from app.schemas.auth import LoginInput, MemberData
from app.schemas.response import ApiSuccess

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
COOKIE_NAME = "gomin_session"
SESSION_SECONDS = 7 * 24 * 60 * 60


def get_auth_settings() -> Settings:
    return get_settings()


def get_auth_repository(database: Annotated[AsyncClient, Depends(get_supabase)]) -> AuthRepository:
    return AuthRepository(database)


def set_session_cookie(response: Response, token: str, settings: Settings):
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True,
                        secure=settings.auth_cookie_secure, samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"


def read_token(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME, "")
    return token if re.fullmatch(r"[A-Za-z0-9_-]{43}", token) else None


async def require_member(
    request: Request, response: Response,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
    settings: Annotated[Settings, Depends(get_auth_settings)],
) -> MemberData:
    token = read_token(request)
    member = await repository.renew_session(token_digest(token)) if token else None
    if not member:
        raise AppError(401, "UNAUTHORIZED", "로그인이 필요하거나 세션이 만료되었습니다. 다시 로그인해 주세요.")
    set_session_cookie(response, token, settings)
    return MemberData(**member)


@router.post("/login", response_model=ApiSuccess[MemberData])
async def login(
    payload: LoginInput, response: Response,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
    settings: Annotated[Settings, Depends(get_auth_settings)],
) -> ApiSuccess[MemberData]:
    member = await repository.find_member(payload.email)
    valid = await run_in_threadpool(verify_password, payload.password.get_secret_value(),
                                   member["password_hash"] if member else DUMMY_PASSWORD_HASH)
    if not valid or not member:
        raise AppError(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호를 확인해 주세요.")
    token = new_session_token()
    await repository.create_session(member["id"], token_digest(token))
    set_session_cookie(response, token, settings)
    return ApiSuccess(data=MemberData(**member))


@router.get("/me", response_model=ApiSuccess[MemberData])
async def me(member: Annotated[MemberData, Depends(require_member)]) -> ApiSuccess[MemberData]:
    return ApiSuccess(data=member)


@router.post("/logout", response_model=ApiSuccess[None])
async def logout(
    request: Request, response: Response,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
    settings: Annotated[Settings, Depends(get_auth_settings)],
) -> ApiSuccess[None]:
    token = read_token(request)
    if token:
        await repository.delete_session(token_digest(token))
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.auth_cookie_secure,
                           httponly=True, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return ApiSuccess(data=None)
