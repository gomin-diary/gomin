from datetime import date, datetime
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


class CollectionListItem(CollectionEntry):
    summary_id: UUID
    conversation_id: UUID
    title: str
    diary_date: date
    emotion_tags: list[str]


class CollectionPage(BaseModel):
    items: list[CollectionListItem]
    next_cursor: str | None


class CollectionDetail(CollectionListItem):
    encouragement_text: str
    completed_at: datetime
    current_feeling: str
    main_concerns: list[str]


class DiaryResult(BaseModel):
    id: UUID
    generation_job_id: UUID
    summary_id: UUID
    conversation_id: UUID
    title: str
    diary_date: date
    completed_at: datetime
    encouragement_text: str
    current_feeling: str
    main_concerns: list[str]
    emotion_tags: list[str]
    collection_entry_id: UUID | None
    saved_at: datetime | None


class ImageJobState(ImageJob):
    result: DiaryResult | None


class ImageAccess(BaseModel):
    url: str
    expires_at: datetime
