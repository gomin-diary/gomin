import re
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, field_validator


class LoginInput(BaseModel):
    email: str = Field(max_length=254)
    password: SecretStr = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Invalid email format")
        return value


class MemberData(BaseModel):
    id: UUID
    email: str
    name: str
