from io import BytesIO
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

from PIL import Image

from app.storage.diary_images import DiaryImageStorage, InvalidDiaryImage, validate_image
from app.storage.supabase import StorageUploadError, SupabaseFileStorage
from test_ai_client import settings


def encoded_image(format="PNG", size=(8, 8)):
    output = BytesIO()
    Image.new("RGB", size, "blue").save(output, format=format)
    return output.getvalue()


class DiaryImageTests(unittest.IsolatedAsyncioTestCase):
    def test_checks_actual_format_size_pixels_and_complete_image(self):
        for format, mime in [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")]:
            data = encoded_image(format)
            self.assertEqual(validate_image(data, max_bytes=10000, max_pixels=100), mime)
        for data, limit, pixels in [(b"", 10000, 100), (b"<svg/>", 10000, 100),
                (encoded_image("GIF"), 10000, 100), (encoded_image(), 1, 100),
                (encoded_image(), 10000, 63), (encoded_image()[:35], 10000, 100)]:
            with self.assertRaises(InvalidDiaryImage):
                validate_image(data, max_bytes=limit, max_pixels=pixels)

    def test_rejects_animation(self):
        output = BytesIO()
        Image.new("RGB", (8, 8), "blue").save(output, format="PNG", save_all=True,
            append_images=[Image.new("RGB", (8, 8), "red")])
        with self.assertRaises(InvalidDiaryImage):
            validate_image(output.getvalue(), max_bytes=10000, max_pixels=100)

    async def test_upload_uses_private_bucket_actual_mime_and_unique_paths(self):
        bucket = SimpleNamespace(upload=AsyncMock())
        async def upload(path, data, file_options):
            return SimpleNamespace(path=path, full_path=f"gomin-diary-images/{path}")
        bucket.upload.side_effect = upload
        client = SimpleNamespace(storage=SimpleNamespace(from_=Mock(return_value=bucket)))
        config = settings(storage_bucket="gomin-diary-images")
        storage = DiaryImageStorage(SupabaseFileStorage(client, config), config)
        first = await storage.upload(encoded_image())
        second = await storage.upload(encoded_image())
        self.assertEqual(first.bucket, "gomin-diary-images")
        self.assertNotEqual(first.path, second.path)
        self.assertEqual(bucket.upload.call_args.kwargs["file_options"],
                         {"content-type": "image/png", "upsert": "false"})

    async def test_invalid_image_never_uploads_and_failure_never_returns_path(self):
        upload = AsyncMock(side_effect=StorageUploadError())
        storage = DiaryImageStorage(SimpleNamespace(upload=upload), settings())
        with self.assertRaises(InvalidDiaryImage):
            await storage.upload(b"invalid")
        upload.assert_not_awaited()
        with self.assertRaises(StorageUploadError):
            await storage.upload(encoded_image())
        upload.assert_awaited_once()
