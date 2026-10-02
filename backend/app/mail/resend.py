import re
from email.headerregistry import Address
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.mail.address import _mailbox
from app.mail.base import Mailer
from app.mail.errors import MailConfigurationError, MailDeliveryError


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
