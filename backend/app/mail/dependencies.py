from app.core.config import get_settings
from app.mail.base import Mailer
from app.mail.resend import ResendMailer
from app.mail.smtp import SmtpMailer


def get_mailer() -> Mailer:
    """Select the configured delivery implementation behind a common interface."""
    settings = get_settings()
    if settings.mail_provider == "smtp":
        return SmtpMailer(settings)
    return ResendMailer(settings)
