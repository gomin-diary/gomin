import asyncio
from typing import Any

from supabase import AsyncClient

from app.core.errors import AppError

# Bound memory used by simultaneous password hashes within each process.
password_slots = asyncio.Semaphore(2)

ERRORS = {
    "EMAIL_EXISTS": (409, "이미 가입된 이메일이에요. 로그인해 주세요."),
    "CODE_MISMATCH": (400, "인증번호가 일치하지 않아요."),
    "CODE_EXPIRED": (400, "인증번호가 만료됐어요. 다시 요청해 주세요."),
    "VERIFICATION_INVALID": (400, "유효하지 않은 인증 요청이에요. 다시 요청해 주세요."),
    "PROOF_INVALID": (400, "이메일 인증이 만료되었거나 유효하지 않아요. 다시 인증해 주세요."),
    "CONSENT_VERSION_CHANGED": (409, "약관이 변경됐어요. 새로고침한 뒤 다시 동의해 주세요."),
    "UNAUTHORIZED": (401, "로그인이 필요합니다."),
}


async def rpc(db: AsyncClient, name: str, params: dict[str, Any]) -> dict:
    try:
        result = (await db.rpc(f"gomin_auth_{name}", params).execute()).data
    except Exception:
        raise AppError(503, "SERVICE_UNAVAILABLE", "서비스를 일시적으로 이용할 수 없습니다.") from None
    if not isinstance(result, dict):
        raise AppError(503, "SERVICE_UNAVAILABLE", "서비스를 일시적으로 이용할 수 없습니다.")
    if code := result.get("error"):
        status, message = ERRORS.get(code, (400, "요청을 확인해 주세요."))
        raise AppError(status, code, message)
    return result
