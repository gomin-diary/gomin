from dataclasses import dataclass
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from storage3.exceptions import StorageException
from supabase import AsyncClient

from app.core.config import Settings


CONTENT_TYPE = re.compile(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+")


class StorageUploadError(Exception):
    def __init__(self) -> None:
        super().__init__("Unable to store file")


@dataclass(frozen=True)
class StoredFile:
    bucket: str
    path: str


class StorageSigningError(Exception):
    def __init__(self) -> None:
        super().__init__("Unable to access image")


@dataclass(frozen=True)
class SignedImage:
    url: str
    expires_at: datetime


class SupabaseFileStorage:
    def __init__(self, client: AsyncClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    async def upload(
        self, data: bytes, *, content_type: str = "application/octet-stream",
    ) -> StoredFile:
        """Store bytes under a unique object path in an existing bucket."""
        if not isinstance(data, bytes) or not data:
            raise ValueError("Non-empty file bytes are required")
        if len(data) > self.settings.storage_max_file_size_bytes:
            raise ValueError("File exceeds the configured size limit")
        if (not isinstance(content_type, str) or len(content_type) > 127
                or not CONTENT_TYPE.fullmatch(content_type)):
            raise ValueError("A MIME type without parameters is required")
        bucket = self.settings.storage_bucket
        path = str(uuid4())
        try:
            result = await self.client.storage.from_(bucket).upload(
                path, data, file_options={"content-type": content_type.lower(), "upsert": "false"},
            )
            if result.path != path or result.full_path != f"{bucket}/{path}":
                raise ValueError("Invalid upload response")
        except (httpx.HTTPError, StorageException, ValueError, KeyError, TypeError, AttributeError):
            # Provider errors may contain credentials. Never retry or expose their text.
            raise StorageUploadError() from None
        return StoredFile(bucket=bucket, path=path)

    async def signed_image(self, bucket: str, path: str) -> SignedImage:
        """Caller must supply an ownership-checked DB reference, never a user path."""
        try:
            if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", bucket)
                    or len(path) > 1024 or not re.fullmatch(r"[A-Za-z0-9_./-]+", path)
                    or path.startswith("/") or any(part in ("", ".", "..") for part in path.split("/"))):
                raise ValueError()
            seconds = self.settings.diary_image_url_seconds
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
            result = await self.client.storage.from_(bucket).create_signed_url(path, seconds)
            url = result["signedURL"]
            parsed, base = httpx.URL(url), httpx.URL(str(self.settings.supabase_url))
            if (parsed.scheme, parsed.host, parsed.port) != (base.scheme, base.host, base.port):
                raise ValueError()
            if (parsed.username or parsed.password or parsed.fragment
                    or parsed.path != f"/storage/v1/object/sign/{bucket}/{path}" or not parsed.params.get("token")):
                raise ValueError()
        except (httpx.HTTPError, StorageException, ValueError, KeyError, TypeError, AttributeError):
            raise StorageSigningError() from None
        return SignedImage(url=url, expires_at=expires_at)
