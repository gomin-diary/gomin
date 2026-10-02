"""Resend delivery only; callers own verification codes and their lifecycle."""

import re
from email.headerregistry import Address
from uuid import uuid4

import httpx

from app.config import Settings, get_settings


class MailConfigurationError(RuntimeError):
    """Server-only email configuration is missing or invalid."""


class MailDeliveryError(RuntimeError):
    """Sanitized delivery result; uncertain requests must keep their reservation."""

    def __init__(self, *, delivery_uncertain: bool, status_code: int | None = None):
        super().__init__("Email delivery status is unknown" if delivery_uncertain
                         else "Email delivery failed")
        self.delivery_uncertain = delivery_uncertain
        self.status_code = status_code


def _mailbox(value: str) -> Address:
    if "\r" in value or "\n" in value:
        raise ValueError("A single email address is required")
    try:
        address = Address(addr_spec=value)
    except ValueError:
        raise ValueError("A single email address is required") from None
    if not address.username or not address.domain:
        raise ValueError("A single email address is required")
    return address


class ResendMailer:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_email(
        self, to: str, subject: str, text: str, *, idempotency_key: str | None = None,
        html: str | None = None,
    ) -> str:
        """Return an API acceptance ID, not proof of inbox delivery. Never retry."""
        config = self.settings
        key = config.resend_api_key.get_secret_value()
        if not key.strip() or not config.resend_from_email:
            raise MailConfigurationError("RESEND_API_KEY and RESEND_FROM_EMAIL must be configured")
        try:
            sender = _mailbox(config.resend_from_email)
            if any(ord(c) < 32 or ord(c) == 127 for c in config.resend_from_name + key):
                raise ValueError("Invalid sender configuration")
            key.encode("ascii")
        except (ValueError, UnicodeEncodeError):
            raise MailConfigurationError("Resend sender configuration is invalid") from None
        recipient = _mailbox(to)
        if "\r" in subject or "\n" in subject:
            raise ValueError("Invalid subject")
        if idempotency_key is None:
            idempotency_key = str(uuid4())
        if not re.fullmatch(r"[\x21-\x7e]{1,256}", idempotency_key):
            raise ValueError("An ASCII idempotency key of 1-256 characters is required")
        payload = {
            "from": str(Address(display_name=config.resend_from_name,
                                username=sender.username, domain=sender.domain)),
            "to": [str(recipient)], "subject": subject, "text": text,
        }
        if html is not None:
            payload["html"] = html
        headers = {"Authorization": f"Bearer {key}", "Idempotency-Key": idempotency_key,
                   "User-Agent": "Gomin/0.1"}
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as client:
            return await self._deliver(client, payload, headers)

    async def send_verification_email(
        self, to: str, code: str, *, idempotency_key: str | None = None, expires_minutes: int = 3,
    ) -> str:
        """Render a caller-provided six-digit code; do not issue or store it."""
        if not re.fullmatch(r"[0-9]{6}", code) or expires_minutes <= 0:
            raise ValueError("A six-digit verification code and positive expiry are required")
        return await self.send_email(
            to, "[Gomin] 회원가입 이메일 인증",
            f"회원가입 이메일 인증번호는 {code}입니다.\n"
            f"{expires_minutes}분 이내에 입력해주세요.\n\n"
            "회원가입을 요청하지 않았다면 이 메일을 무시해주세요.",
            idempotency_key=idempotency_key,
        )

    async def _deliver(self, client: httpx.AsyncClient, payload: dict, headers: dict) -> str:
        try:
            response = await client.post(
                "https://api.resend.com/emails", json=payload, headers=headers,
                timeout=self.settings.resend_timeout_seconds, follow_redirects=False,
            )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            raise MailDeliveryError(delivery_uncertain=False) from None
        except httpx.HTTPError:
            # A write/read failure may happen after the provider accepted the message.
            raise MailDeliveryError(delivery_uncertain=True) from None
        if not 200 <= response.status_code < 300:
            # 409 can mean a request with the same key is still being processed.
            uncertain = not 400 <= response.status_code < 500 or response.status_code == 409
            raise MailDeliveryError(delivery_uncertain=uncertain,
                                    status_code=response.status_code) from None
        try:
            result = response.json()
            email_id = result.get("id") if isinstance(result, dict) else None
            if not isinstance(email_id, str) or not email_id.strip():
                raise ValueError("Invalid acceptance response")
        except ValueError:
            raise MailDeliveryError(delivery_uncertain=True) from None
        return email_id


def get_mailer() -> ResendMailer:
    """Use directly or as a FastAPI dependency with Depends(get_mailer)."""
    return ResendMailer(get_settings())
