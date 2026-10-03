import asyncio
import secrets
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Response
from supabase import AsyncClient

from app.auth.session import set_session_cookie
from app.auth.crypto import code_digest
from app.auth.security import hash_password, new_session_token, token_digest
from app.auth.service import password_slots, rpc
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.client import get_supabase
from app.mail import Mailer, get_mailer
from app.mail.errors import MailConfigurationError, MailDeliveryError
from app.schemas.auth import MemberData
from app.schemas.response import ApiSuccess
from app.schemas.signup import EmailInput, ProofData, SignupInput, VerificationData, VerifyInput

router = APIRouter(prefix="/api/v1/auth", tags=["signup"])
Database = Annotated[AsyncClient, Depends(get_supabase)]
Config = Annotated[Settings, Depends(get_settings)]


def hmac_key(settings: Settings) -> str:
    key = settings.auth_hmac_key.get_secret_value()
    if len(key.encode()) < 32:
        raise AppError(503, "AUTH_NOT_CONFIGURED", "이메일 인증 서비스를 준비하고 있어요.")
    return key


@router.post("/email-verifications", response_model=ApiSuccess[VerificationData])
async def request_verification(payload: EmailInput, response: Response, db: Database, settings: Config,
                               mailer: Annotated[Mailer, Depends(get_mailer)]):
    key = hmac_key(settings)
    request_id = uuid4()
    code = f"{secrets.randbelow(1_000_000):06d}"
    await rpc(db, "begin_verification", {"p_id": str(request_id), "p_email": payload.email,
               "p_code_hmac": code_digest(key, request_id, payload.email, code)})
    try:
        await mailer.send_verification_email(payload.email, code=code, expires_minutes=3,
                                            idempotency_key=f"signup-verification/{request_id}")
    except MailDeliveryError as error:
        if not error.delivery_uncertain:
            await rpc(db, "finish_delivery", {"p_id": str(request_id), "p_sent": False})
        raise AppError(503, "MAIL_DELIVERY_UNCERTAIN" if error.delivery_uncertain else "MAIL_DELIVERY_FAILED",
                       "메일 발송 결과를 확인할 수 없어요. 새 인증번호를 요청해 주세요." if error.delivery_uncertain
                       else "인증 메일을 발송하지 못했어요. 다시 요청해 주세요.") from None
    except MailConfigurationError:
        await rpc(db, "finish_delivery", {"p_id": str(request_id), "p_sent": False})
        raise AppError(503, "MAIL_NOT_CONFIGURED", "인증 메일 서비스를 준비하고 있어요.") from None
    result = await rpc(db, "finish_delivery", {"p_id": str(request_id), "p_sent": True})
    response.headers["Cache-Control"] = "no-store"
    return ApiSuccess(data=VerificationData(verification_id=request_id, **result))


@router.post("/email-verifications/confirm", response_model=ApiSuccess[ProofData])
async def confirm_verification(payload: VerifyInput, response: Response, db: Database, settings: Config):
    key = hmac_key(settings)
    proof = new_session_token()
    result = await rpc(db, "verify_code", {
        "p_id": str(payload.verification_id), "p_email": payload.email,
        "p_code_hmac": code_digest(key, payload.verification_id, payload.email, payload.code.get_secret_value()),
        "p_proof_digest": token_digest(proof),
    })
    response.headers["Cache-Control"] = "no-store"
    return ApiSuccess(data=ProofData(verification_proof=proof, **result))


@router.post("/signup", response_model=ApiSuccess[MemberData], status_code=201)
async def signup(payload: SignupInput, response: Response, db: Database, settings: Config):
    versions = {item.type: item.version for item in payload.consents}
    if versions["terms_of_service"] != settings.auth_terms_version or versions["privacy_collection"] != settings.auth_privacy_version:
        raise AppError(409, "CONSENT_VERSION_CHANGED", "약관이 변경됐어요. 새로고침한 뒤 다시 동의해 주세요.")
    async with password_slots:
        password_hash = await asyncio.to_thread(hash_password, payload.password.get_secret_value())
    token = new_session_token()
    result = await rpc(db, "signup", {
        "p_email": payload.email, "p_name": payload.name, "p_password_hash": password_hash,
        "p_proof_digest": token_digest(payload.verification_proof.get_secret_value()),
        "p_session_digest": token_digest(token), "p_terms_version": versions["terms_of_service"],
        "p_privacy_version": versions["privacy_collection"], "p_expected_terms": settings.auth_terms_version,
        "p_expected_privacy": settings.auth_privacy_version,
    })
    set_session_cookie(response, token, settings)
    return ApiSuccess(data=MemberData(**result))
