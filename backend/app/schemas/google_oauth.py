from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from app.schemas.signup import ConsentInput

class StartData(BaseModel):
    authorization_url: str

class PendingData(BaseModel):
    email: str
    profile_name: str | None
    expires_at: datetime
    csrf_token: str

class CancelInput(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    csrf_token: SecretStr = Field(min_length=1, max_length=256)

class GoogleSignupInput(CancelInput):
    name: str = Field(min_length=1, max_length=1000)
    consents: list[ConsentInput] = Field(min_length=2, max_length=2)

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value: str):
        value = value.strip()
        if not 1 <= len(value) <= 30:
            raise ValueError('Invalid name')
        return value

    @model_validator(mode='after')
    def validate_consents(self):
        if {c.type for c in self.consents} != {'terms_of_service', 'privacy_collection'}:
            raise ValueError('Both consents are required')
        return self
