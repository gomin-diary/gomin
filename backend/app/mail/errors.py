class MailConfigurationError(RuntimeError):
    """Server-only email configuration is missing or invalid."""


class MailDeliveryError(RuntimeError):
    """Sanitized delivery result; uncertain requests must keep their reservation."""

    def __init__(self, *, delivery_uncertain: bool, status_code: int | None = None):
        super().__init__("Email delivery status is unknown" if delivery_uncertain
                         else "Email delivery failed")
        self.delivery_uncertain = delivery_uncertain
        self.status_code = status_code
