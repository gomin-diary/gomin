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
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]
    auth_cookie_secure: bool = True
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
