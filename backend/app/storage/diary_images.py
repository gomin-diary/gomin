import asyncio
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.core.config import Settings
from app.storage.supabase import StoredFile, SupabaseFileStorage


class InvalidDiaryImage(ValueError):
    def __init__(self) -> None:
        super().__init__("Invalid diary image")


def validate_image(data: bytes, *, max_bytes: int, max_pixels: int) -> str:
    """Verify the actual single-frame image before uploading untrusted provider bytes."""
    if not isinstance(data, bytes) or not data or len(data) > max_bytes:
        raise InvalidDiaryImage()
    try:
        with Image.open(BytesIO(data), formats=["PNG", "JPEG", "WEBP"]) as image:
            if image.width * image.height > max_pixels or getattr(image, "n_frames", 1) != 1:
                raise InvalidDiaryImage()
            content_type = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[image.format]
            image.verify()
        # verify() does not decode pixels for every format. Fully decode a fresh reader.
        with Image.open(BytesIO(data), formats=["PNG", "JPEG", "WEBP"]) as image:
            image.load()
        return content_type
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise InvalidDiaryImage() from None


class DiaryImageStorage:
    def __init__(self, storage: SupabaseFileStorage, settings: Settings) -> None:
        self.storage = storage
        self.settings = settings

    async def upload(self, data: bytes) -> StoredFile:
        content_type = await asyncio.to_thread(
            validate_image, data,
            max_bytes=min(self.settings.storage_max_file_size_bytes, 10485760),
            max_pixels=self.settings.diary_image_max_pixels,
        )
        return await self.storage.upload(data, content_type=content_type)
