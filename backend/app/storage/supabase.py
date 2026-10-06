from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx
from storage3.exceptions import StorageException
from storage3.types import CreateSignedUploadUrlOptions
from supabase import AsyncClient

from app.core.config import Settings


class StorageSigningError(Exception):
    def __init__(self) -> None:
        super().__init__("Unable to create a Storage upload URL")


@dataclass(frozen=True)
class SignedUpload:
    bucket: str
    path: str
    upload_url: str = field(repr=False)
    expires_in: int = 7200


class SupabaseFileStorage:
    def __init__(self, client: AsyncClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    async def create_upload_url(self, owner_id: UUID) -> SignedUpload:
        """Grant creation-only access to a new owner path; this does not upload a file."""
        if not isinstance(owner_id, UUID):
            raise ValueError("A UUID owner is required")
        bucket = self.settings.storage_bucket
        path = f"{owner_id}/{uuid4()}"
        try:
            result = await self.client.storage.from_(bucket).create_signed_upload_url(
                path, options=CreateSignedUploadUrlOptions(upsert="false"),
            )
            upload_url = result['signed_url']
            actual = urlsplit(upload_url)
            base = urlsplit(str(self.settings.supabase_url))
            expected_path = base.path.rstrip('/') + f'/storage/v1/object/upload/sign/{bucket}/{path}'
            if (actual.scheme != base.scheme or actual.netloc != base.netloc
                    or actual.path != expected_path or actual.fragment
                    or not parse_qs(actual.query).get('token')):
                raise ValueError("Invalid signed upload response")
        except (httpx.HTTPError, StorageException, ValueError, KeyError, TypeError, AttributeError):
            # Provider error text and signed URLs may contain secrets. Never retry or chain them.
            raise StorageSigningError() from None
        return SignedUpload(bucket=bucket, path=path, upload_url=upload_url)
