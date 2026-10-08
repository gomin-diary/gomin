import asyncio
import base64
import binascii
import json
import re

import httpx

from app.core.config import Settings


class AIConfigurationError(Exception):
    """Configuration errors contain field names only, never secret values."""


class AIRequestError(Exception):
    def __init__(self, code: str, *, uncertain: bool, status_code: int | None = None) -> None:
        super().__init__("AI provider request failed")
        self.code = code
        self.uncertain = uncertain
        self.status_code = status_code


class CodysseyClient:
    """Use the app's HTTP client without retrying or exposing provider errors."""

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

    async def _json_response(self, request: httpx.Request, *, max_bytes: int) -> dict:
        response = None
        try:
            async with asyncio.timeout(self.settings.ai_timeout_seconds):
                response = await self.http_client.send(request, stream=True, follow_redirects=False)
                if not 200 <= response.status_code < 300:
                    code = "RATE_LIMITED" if response.status_code == 429 else "PROVIDER_ERROR"
                    raise AIRequestError(code, uncertain=response.status_code >= 500 or
                                         response.status_code in (408, 409),
                                         status_code=response.status_code)
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > max_bytes:
                        raise AIRequestError("RESPONSE_TOO_LARGE", uncertain=True)
                    body.extend(chunk)
                parsed = json.loads(body)
                if not isinstance(parsed, dict):
                    raise ValueError("Invalid JSON object")
                return parsed
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            raise AIRequestError("CONNECTION_FAILED", uncertain=False) from None
        except (TimeoutError, httpx.TimeoutException):
            raise AIRequestError("TIMEOUT", uncertain=True) from None
        except httpx.HTTPError:
            raise AIRequestError("PROVIDER_ERROR", uncertain=True) from None
        except (ValueError, UnicodeError):
            raise AIRequestError("INVALID_RESPONSE", uncertain=True) from None
        finally:
            if response is not None:
                try:
                    await response.aclose()
                except httpx.HTTPError:
                    raise AIRequestError("PROVIDER_ERROR", uncertain=True) from None

    async def generate_text(self, messages: list[dict[str, str]]) -> str:
        payload = await self._json_response(self.build_text_request(messages), max_bytes=65536)
        try:
            choice = payload["choices"][0]
            message = choice["message"]
            content = message["content"]
            if choice["finish_reason"] != "stop" or message["role"] != "assistant" or not isinstance(content, str) or not content.strip():
                raise ValueError()
            return content
        except (KeyError, IndexError, TypeError, ValueError):
            raise AIRequestError("INVALID_RESPONSE", uncertain=True) from None

    async def generate_image(self, prompt: str, *, size: str) -> bytes:
        """Receive Base64 bytes; the caller validates the image before uploading."""
        if not isinstance(prompt, str) or not prompt.strip() or not isinstance(size, str) or not size.strip():
            raise ValueError("Image prompt and size must not be blank")
        max_bytes = self.settings.storage_max_file_size_bytes
        encoded_limit = 4 * ((max_bytes + 2) // 3)
        payload = await self._json_response(self.build_image_request(prompt, size=size),
                                            max_bytes=encoded_limit + 65536)
        try:
            encoded = payload["result"]["images"][0]["b64_json"]
            if not isinstance(encoded, str) or not encoded or len(encoded) > encoded_limit:
                raise ValueError("Invalid encoded image")
            data = base64.b64decode(encoded, validate=True)
            if not data or len(data) > max_bytes:
                raise ValueError("Invalid image size")
        except (KeyError, IndexError, TypeError, ValueError, binascii.Error):
            raise AIRequestError("INVALID_RESPONSE", uncertain=True) from None
        return data
