from dataclasses import dataclass
import re
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
