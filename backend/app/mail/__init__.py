"""Public mail interface and provider implementations."""

from app.mail.base import Mailer
from app.mail.dependencies import get_mailer
from app.mail.errors import MailConfigurationError, MailDeliveryError
from app.mail.resend import ResendMailer
from app.mail.smtp import SmtpMailer

__all__ = [
    "Mailer", "MailConfigurationError", "MailDeliveryError",
    "ResendMailer", "SmtpMailer", "get_mailer",
]
