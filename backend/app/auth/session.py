"""Shared session dependencies and cookies for all authentication flows."""

import re
from typing import Annotated

from fastapi import Depends, Request, Response
from supabase import AsyncClient

from app.auth.repository import AuthRepository
from app.auth.security import token_digest
from app.core import config
from app.core.config import Settings
from app.core.errors import AppError
from app.db.client import get_supabase
from app.schemas.auth import MemberData

COOKIE_NAME = "gomin_session"
SESSION_SECONDS = 7 * 24 * 60 * 60


def get_auth_settings() -> Settings:
    return config.get_settings()


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
