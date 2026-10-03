from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from app.mail.address import _mailbox


class EmailInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: str = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        address = _mailbox(value)
        if address.addr_spec != value or "." not in address.domain or any(c.isspace() for c in value):
            raise ValueError("Invalid email")
        return value


class VerifyInput(EmailInput):
    verification_id: UUID
    code: SecretStr = Field(min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def numeric_code(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().isascii() or not value.get_secret_value().isdigit():
            raise ValueError("Invalid code")
        return value


class ConsentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["terms_of_service", "privacy_collection"]
    version: str = Field(min_length=1, max_length=100)
    agreed: Literal[True]


class SignupInput(EmailInput):
    name: str = Field(min_length=1, max_length=1000)
    password: SecretStr = Field(min_length=8, max_length=1024)
    confirmation: SecretStr = Field(min_length=8, max_length=1024)
    verification_proof: SecretStr = Field(min_length=43, max_length=43)
    consents: list[ConsentInput] = Field(min_length=2, max_length=2)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= 30:
            raise ValueError("Invalid name")
        return value

    @model_validator(mode="after")
    def validate_signup(self):
        if self.password.get_secret_value() != self.confirmation.get_secret_value():
            raise ValueError("Passwords must match")
        if {item.type for item in self.consents} != {"terms_of_service", "privacy_collection"}:
            raise ValueError("Both consents are required")
        return self


class VerificationData(BaseModel):
    verification_id: UUID
    expires_at: datetime


class ProofData(BaseModel):
    verification_proof: str
    expires_at: datetime
