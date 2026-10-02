import asyncio
import smtplib
import ssl
from email.headerregistry import Address
from email.message import EmailMessage

from app.core.config import Settings
from app.mail.address import _mailbox
from app.mail.base import Mailer
from app.mail.errors import MailConfigurationError, MailDeliveryError


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
