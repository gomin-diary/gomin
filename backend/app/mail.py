"""Common mail interface with SMTP and Resend delivery implementations."""

import asyncio
import re
import smtplib
import ssl
from abc import ABC, abstractmethod
from email.headerregistry import Address
from email.message import EmailMessage
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


class Mailer(ABC):
    @abstractmethod
    async def send_email(
        self, to: str, subject: str, text: str, *, html: str | None = None,
        idempotency_key: str | None = None,
    ) -> str | None:
        """Send one message; success means provider acceptance, not inbox delivery."""
        raise NotImplementedError

    async def send_verification_email(
        self, to: str, code: str, *, idempotency_key: str | None = None, expires_minutes: int = 3,
    ) -> str | None:
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


class ResendMailer(Mailer):
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


class SmtpMailer(Mailer):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_email(
        self, to: str, subject: str, text: str, *, html: str | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        """SMTP acceptance only; SMTP does not support provider idempotency keys."""
        config = self.settings
        if not config.smtp_username or not config.smtp_password.get_secret_value().strip():
            raise MailConfigurationError("SMTP_USERNAME and SMTP_PASSWORD must be configured")
        try:
            sender = _mailbox(config.smtp_username)
            if "\r" in config.smtp_from_name or "\n" in config.smtp_from_name:
                raise ValueError("Invalid sender name")
        except ValueError:
            raise MailConfigurationError("SMTP sender configuration is invalid") from None
        recipient = _mailbox(to)
        message = EmailMessage()
        message["From"] = Address(
            display_name=config.smtp_from_name,
            username=sender.username,
            domain=sender.domain,
        )
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(text)
        if html is not None:
            message.add_alternative(html, subtype="html")
        await asyncio.to_thread(self._deliver, message)

    def _deliver(self, message: EmailMessage) -> None:
        config = self.settings
        context = ssl.create_default_context()
        accepted = False
        try:
            if config.smtp_port == 465:
                connection = smtplib.SMTP_SSL(
                    config.smtp_host, config.smtp_port,
                    timeout=config.smtp_timeout_seconds, context=context,
                )
            else:
                connection = smtplib.SMTP(
                    config.smtp_host, config.smtp_port, timeout=config.smtp_timeout_seconds
                )
            with connection as smtp:
                if config.smtp_port == 587:
                    smtp.ehlo()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                smtp.login(config.smtp_username, config.smtp_password.get_secret_value())
                if smtp.send_message(message):
                    raise MailDeliveryError(delivery_uncertain=False)
                accepted = True
        except (smtplib.SMTPResponseException, smtplib.SMTPRecipientsRefused):
            if accepted:
                return
            raise MailDeliveryError(delivery_uncertain=False) from None
        except (smtplib.SMTPException, OSError):
            if accepted:
                return
            # Disconnects/timeouts may occur after the server accepted the message.
            raise MailDeliveryError(delivery_uncertain=True) from None


def get_mailer() -> Mailer:
    """Select the configured delivery implementation behind a common interface."""
    settings = get_settings()
    if settings.mail_provider == "smtp":
        return SmtpMailer(settings)
    return ResendMailer(settings)
