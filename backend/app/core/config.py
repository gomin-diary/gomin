import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: HttpUrl
    supabase_secret_key: SecretStr
    storage_bucket: str = "gomin-files"
    storage_max_file_size_bytes: int = Field(default=10485760, gt=0)
    diary_image_bucket: str = "gomin-diary-images"
    diary_image_max_pixels: int = Field(default=16777216, gt=0, le=16777216)
    diary_image_url_seconds: int = Field(default=300, ge=60, le=3600)
    ai_base_url: HttpUrl = HttpUrl("https://copa.codyssey.kr")
    ai_api_key: SecretStr = SecretStr("")
    ai_text_model: str = Field(default="gpt-5.4-mini", min_length=1)
    ai_timeout_seconds: float = Field(default=120, gt=0, le=600, allow_inf_nan=False)
    gemini_base_url: HttpUrl = HttpUrl("https://generativelanguage.googleapis.com")
    gemini_api_key: SecretStr = SecretStr("")
    gemini_image_model: str = "gemini-2.5-flash-image"
    gemini_image_aspect_ratio: Literal["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"] = "1:1"
    gemini_timeout_seconds: float = Field(default=120, gt=0, le=600, allow_inf_nan=False)
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]
    auth_hmac_key: SecretStr = SecretStr("")
    auth_cookie_secure: bool = True
    auth_terms_version: str = "dev-2026-10-02"
    auth_privacy_version: str = "dev-2026-10-02"
    google_oauth_client_id: str = ''
    google_oauth_client_secret: SecretStr = SecretStr('')
    google_oauth_redirect_uri: str = ''
    auth_frontend_origin: str = ''
    auth_oauth_encryption_key: SecretStr = SecretStr('')
    mail_provider: Literal["resend", "smtp"] = "resend"
    resend_api_key: SecretStr = SecretStr("")
    resend_from_email: str = ""
    resend_from_name: str = "Gomin"
    resend_timeout_seconds: float = Field(default=10, gt=0, le=60, allow_inf_nan=False)

    smtp_host: str = Field(default="smtp.gmail.com", min_length=1)
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from_name: str = "Gomin"
    smtp_timeout_seconds: float = Field(default=10, gt=0, le=60, allow_inf_nan=False)

    @field_validator("smtp_port")
    @classmethod
    def validate_smtp_port(cls, value: int) -> int:
        if value not in (587, 465):
            raise ValueError("SMTP_PORT must be 587 (STARTTLS) or 465 (TLS)")
        return value

    @field_validator("supabase_secret_key")
    @classmethod
    def validate_secret_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("SUPABASE_SECRET_KEY must be configured")
        return value

    @field_validator("storage_bucket", "diary_image_bucket")
    @classmethod
    def validate_storage_bucket(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", value):
            raise ValueError("STORAGE_BUCKET must be a bucket ID of 1-100 characters")
        return value

    @field_validator("ai_base_url", "gemini_base_url")
    @classmethod
    def validate_ai_base_url(cls, value: HttpUrl) -> HttpUrl:
        if (value.scheme != "https" or value.username or value.password
                or value.query is not None or value.fragment is not None
                or value.path not in (None, "", "/")):
            raise ValueError("AI base URL must be an HTTPS origin without a path or credentials")
        return value

    @field_validator("ai_text_model")
    @classmethod
    def validate_ai_model(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", value):
            raise ValueError("AI model must be an identifier without whitespace")
        return value

    @field_validator("gemini_image_model")
    @classmethod
    def validate_gemini_model(cls, value: str) -> str:
        if value and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
            raise ValueError("Gemini model must be a model ID without path separators")
        return value

    @property
    def ai_openai_base_url(self) -> str:
        return str(self.ai_base_url).rstrip("/") + "/v1"

    @property
    def ai_text_url(self) -> str:
        return self.ai_openai_base_url + "/chat/completions"

    @property
    def gemini_image_url(self) -> str:
        return str(self.gemini_base_url).rstrip("/") + f"/v1beta/models/{self.gemini_image_model}:generateContent"


@lru_cache
def get_settings() -> Settings:
    return Settings()
