from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary_id: UUID
    idempotency_key: UUID


class ImageJob(BaseModel):
    id: UUID
    conversation_id: UUID
    input_summary_id: UUID
    status: Literal["queued", "running", "failed", "succeeded"]
    attempt_count: int
    error_code: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class CollectionEntry(BaseModel):
    id: UUID
    source_result_id: UUID
    saved_at: datetime
