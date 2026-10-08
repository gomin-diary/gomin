from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GenerateDiaryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary_id: UUID


class DiarySummary(BaseModel):
    id: UUID
    current_feeling: str
    main_concerns: list[str]
    emotion_tags: list[str]


class DiaryResult(BaseModel):
    id: UUID
    summary_id: UUID
    title: str
    encouragement_text: str
    diary_date: date
    image_url: str
