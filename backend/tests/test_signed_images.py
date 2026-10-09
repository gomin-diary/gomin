from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

from app.storage.supabase import StorageSigningError, SupabaseFileStorage
from test_ai_client import settings


class SignedImageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bucket = SimpleNamespace(create_signed_url=AsyncMock(return_value={
            "signedURL": "https://example.supabase.co/storage/v1/object/sign/private/object?token=test-only"}))
        client = SimpleNamespace(storage=SimpleNamespace(from_=Mock(return_value=self.bucket)))
        self.storage = SupabaseFileStorage(client, settings())

    async def test_signs_database_reference_with_expiry(self):
        result = await self.storage.signed_image("private", "object")
        self.assertTrue(result.url.startswith("https://example.supabase.co/"))
        self.assertGreater(result.expires_at, datetime.now(timezone.utc))
        self.bucket.create_signed_url.assert_awaited_once_with("object", 300)

    async def test_rejects_paths_and_unsafe_provider_url_without_leaking_response(self):
        for path in ["../object", "/object", "object?token=x", "a//b"]:
            with self.assertRaises(StorageSigningError):
                await self.storage.signed_image("private", path)
        self.bucket.create_signed_url.assert_not_awaited()
        for url in ["https://other.example/storage/v1/object/sign/private/object?token=private",
                    "https://example.supabase.co/storage/v1/object/public/private/object",
                    "https://example.supabase.co/storage/v1/object/sign/private/another?token=private"]:
            self.bucket.create_signed_url.return_value = {"signedURL": url}
            with self.assertRaises(StorageSigningError) as error:
                await self.storage.signed_image("private", "object")
            self.assertEqual(str(error.exception), "Unable to access image")
