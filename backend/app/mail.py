"""SMTP delivery only; callers own verification codes and their lifecycle."""

import asyncio
import smtplib
import ssl
from email.headerregistry import Address
from email.message import EmailMessage

from app.config import Settings, get_settings


class MailConfigurationError(RuntimeError):
    """SMTP credentials are missing or invalid."""


class MailDeliveryError(RuntimeError):
    """The SMTP server did not accept the message."""


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


class SmtpMailer:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_email(
        self, to: str, subject: str, text: str, *, html: str | None = None
    ) -> None:
        """Send one message; return only after SMTP acceptance, not inbox delivery."""
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

    async def send_verification_email(
        self, to: str, code: str, *, expires_minutes: int = 10
    ) -> None:
        """Render a caller-provided code; this method does not issue or store codes."""
        if not code.strip() or expires_minutes <= 0:
            raise ValueError("A verification code and positive expiry are required")
        await self.send_email(
            to,
            "[Gomin] 회원가입 이메일 인증",
            f"회원가입 이메일 인증번호는 {code}입니다.\n"
            f"{expires_minutes}분 이내에 입력해주세요.\n\n"
            "회원가입을 요청하지 않았다면 이 메일을 무시해주세요.",
        )

    def _deliver(self, message: EmailMessage) -> None:
        config = self.settings
        context = ssl.create_default_context()
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
                    raise MailDeliveryError("Email delivery failed")
        except (smtplib.SMTPException, OSError):
            # Never surface SMTP responses, which can contain credentials or addresses.
            raise MailDeliveryError("Email delivery failed") from None


def get_mailer() -> SmtpMailer:
    """Use directly or as a FastAPI dependency with Depends(get_mailer)."""
    return SmtpMailer(get_settings())
