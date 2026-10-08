from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=100)
    client_message_id: UUID

    @field_validator("content")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message must contain text")
        return value


class SummaryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID


class SummaryContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_feeling: str = Field(min_length=1, max_length=2000)
    main_concerns: list[str] = Field(min_length=1, max_length=20)
    emotion_tags: list[str] = Field(min_length=1, max_length=20)

    @field_validator("current_feeling")
    @classmethod
    def feeling_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Empty feeling")
        return value

    @field_validator("main_concerns", "emotion_tags")
    @classmethod
    def items_nonblank(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > 1000 for value in values):
            raise ValueError("Invalid summary items")
        return values


class MessageData(BaseModel):
    id: UUID
    conversation_id: UUID
    seq_no: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class SummaryData(SummaryContent):
    # RPC/table rows contain ownership and generation linkage; keep those
    # internal while retaining strict validation of provider output above.
    model_config = ConfigDict(extra="ignore")
    id: UUID
    conversation_id: UUID
    version: int
    source_until_seq_no: int
    confirmed_at: datetime | None
    created_at: datetime


class JobData(BaseModel):
    id: UUID
    kind: Literal["reply", "summary"]
    status: Literal["running", "succeeded", "failed"]
    source_until_seq_no: int
    error_code: str | None


class ConversationData(BaseModel):
    id: UUID
    phase: str
    messages: list[MessageData]
    summaries: list[SummaryData]
    jobs: list[JobData]


class AcceptedMessage(BaseModel):
    message: MessageData
    job: JobData


class ConfirmedSummaryHandoff(BaseModel):
    conversation_id: UUID
    summary_id: UUID
    version: int
    confirmed: Literal[True] = True
    summary: SummaryData
    next_stage: Literal["image_generation"] = "image_generation"
    next_stage_status: Literal["not_started"] = "not_started"
