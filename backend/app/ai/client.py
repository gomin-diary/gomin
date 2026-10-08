import re

import httpx

from app.core.config import Settings


class AIConfigurationError(Exception):
    """Configuration errors contain field names only, never secret values."""


class CodysseyClient:
    """Build provider requests with the app's shared HTTP client; does not send them."""

    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self.http_client = http_client
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        key = self.settings.ai_api_key.get_secret_value()
        if not re.fullmatch(r"[\x21-\x7e]+", key):
            raise AIConfigurationError("AI_API_KEY must be a non-empty ASCII token")
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def build_text_request(self, messages: list[dict[str, str]]) -> httpx.Request:
        return self.http_client.build_request(
            "POST", self.settings.ai_text_url, headers=self._headers(),
            json={"model": self.settings.ai_text_model, "messages": messages},
            timeout=self.settings.ai_timeout_seconds,
        )

    def build_image_request(self, prompt: str, *, size: str) -> httpx.Request:
        if not self.settings.ai_image_model:
            raise AIConfigurationError("AI_IMAGE_MODEL must be configured")
        return self.http_client.build_request(
            "POST", self.settings.ai_image_url, headers=self._headers(),
            json={"model": self.settings.ai_image_model, "prompt": prompt, "size": size,
                  "response_format": self.settings.ai_image_response_format},
            timeout=self.settings.ai_timeout_seconds,
        )
