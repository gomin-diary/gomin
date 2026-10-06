import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UploadUrlInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=255)
    size: int = Field(gt=0, strict=True)
    content_type: str = Field(max_length=127)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        if not value.strip() or value in ('.', '..') or any(
            c in '/\\' or ord(c) < 32 or ord(c) == 127 for c in value
        ):
            raise ValueError("A filename without path separators or control characters is required")
        return value

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*", value):
            raise ValueError("A MIME type without parameters is required")
        return value.lower()


class UploadUrlData(BaseModel):
    bucket: str
    path: str
    upload_url: str = Field(repr=False)
    expires_in: int
    max_file_size_bytes: int
