import base64
import binascii
from datetime import datetime
import json
from uuid import UUID

from app.core.errors import AppError


def decode_cursor(value: str | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    try:
        if len(value) > 512:
            raise ValueError()
        parsed = json.loads(base64.b64decode(value, altchars=b"-_", validate=True))
        if not isinstance(parsed, list) or len(parsed) != 2:
            raise ValueError()
        timestamp = datetime.fromisoformat(parsed[0])
        if timestamp.tzinfo is None:
            raise ValueError()
        return timestamp.isoformat(), str(UUID(parsed[1]))
    except (ValueError, TypeError, binascii.Error, AttributeError):
        raise AppError(422, "INVALID_CURSOR", "조회 위치를 확인해 주세요.") from None


def encode_cursor(saved_at: datetime, id: UUID) -> str:
    return base64.urlsafe_b64encode(json.dumps([saved_at.isoformat(), str(id)]).encode()).decode()
