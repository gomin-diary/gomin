"""Current-member lookup and logout shared by login and signup."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.auth.repository import AuthRepository
from app.auth.security import token_digest
from app.auth.session import COOKIE_NAME, get_auth_repository, get_auth_settings, read_token, require_member
from app.core.config import Settings
from app.schemas.auth import MemberData
from app.schemas.response import ApiSuccess

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
