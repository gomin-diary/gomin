import hashlib
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.auth.session import require_member
from app.core.config import Settings
from app.core.errors import AppError
from app.diary.repository import DiaryRepository, get_diary_repository
from app.schemas.auth import MemberData
from app.schemas.diary import CollectionEntry, ImageJob, ImageRequest
from app.schemas.response import ApiSuccess
from app.storage.dependencies import get_storage_settings

router = APIRouter(prefix="/api/v1", tags=["diary"])


@router.post("/conversations/{conversation_id}/image-jobs", response_model=ApiSuccess[ImageJob], status_code=202)
async def submit_image(
    conversation_id: UUID, body: ImageRequest, response: Response,
    member: Annotated[MemberData, Depends(require_member)],
    repository: Annotated[DiaryRepository, Depends(get_diary_repository)],
    settings: Annotated[Settings, Depends(get_storage_settings)],
) -> ApiSuccess[ImageJob]:
    if not settings.ai_image_model:
        raise AppError(503, "AI_NOT_CONFIGURED", "이미지 생성 설정을 준비 중입니다.")
    inputs = {"conversation_id": str(conversation_id), "summary_id": str(body.summary_id),
              "text_model": settings.ai_text_model, "image_model": settings.ai_image_model,
              "size": settings.ai_image_size, "prompt_version": "diary-v1"}
    fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    job = await repository.rpc("submit_diary_image", {
        "p_member_id": str(member.id), "p_conversation_id": str(conversation_id),
        "p_summary_id": str(body.summary_id), "p_idempotency_key": str(body.idempotency_key),
        "p_fingerprint": fingerprint, "p_text_model": settings.ai_text_model,
        "p_image_model": settings.ai_image_model, "p_image_size": inputs["size"],
    })
    response.headers["Cache-Control"] = "no-store"
    return ApiSuccess(data=ImageJob.model_validate(job))


@router.post("/diary-results/{result_id}/collection-entry", response_model=ApiSuccess[CollectionEntry])
async def save_result(
    result_id: UUID, response: Response,
    member: Annotated[MemberData, Depends(require_member)],
    repository: Annotated[DiaryRepository, Depends(get_diary_repository)],
) -> ApiSuccess[CollectionEntry]:
    entry = await repository.rpc("save_collection_result", {
        "p_member_id": str(member.id), "p_result_id": str(result_id),
    })
    response.headers["Cache-Control"] = "no-store"
    return ApiSuccess(data=CollectionEntry.model_validate(entry))
