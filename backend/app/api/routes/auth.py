from typing import Annotated

from fastapi import APIRouter, Depends, Response
from starlette.concurrency import run_in_threadpool

from app.auth.repository import AuthRepository
from app.auth.security import DUMMY_PASSWORD_HASH, new_session_token, token_digest, verify_password
from app.auth.session import get_auth_repository, get_auth_settings, set_session_cookie
from app.core.config import Settings
from app.core.errors import AppError
from app.schemas.auth import LoginInput, MemberData
from app.schemas.response import ApiSuccess

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=ApiSuccess[MemberData])
async def login(
    payload: LoginInput, response: Response,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
    settings: Annotated[Settings, Depends(get_auth_settings)],
) -> ApiSuccess[MemberData]:
    member = await repository.find_member(payload.email)
    valid = await run_in_threadpool(verify_password, payload.password.get_secret_value(),
                                   (member.get("password_hash") if member else None) or DUMMY_PASSWORD_HASH)
    if not valid or not member:
        raise AppError(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호를 확인해 주세요.")
    token = new_session_token()
    await repository.create_session(member["id"], token_digest(token))
    set_session_cookie(response, token, settings)
    return ApiSuccess(data=MemberData(**member))
