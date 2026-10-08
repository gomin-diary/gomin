from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.ai.client import AIConfigurationError, AIRequestError, CodysseyClient
from app.ai.dependencies import get_ai_client
from app.auth.session import require_member
from app.core.errors import AppError
from app.diary.composition import compose_diary
from app.diary.repository import DiaryRepository, get_diary_repository
from app.schemas.auth import MemberData
from app.schemas.diary import DiaryResult, DiarySummary, GenerateDiaryInput
from app.schemas.response import ApiSuccess
from app.storage.dependencies import get_diary_image_storage, get_file_storage
from app.storage.diary_images import DiaryImageStorage, InvalidDiaryImage
from app.storage.supabase import StorageSigningError, StorageUploadError, SupabaseFileStorage

router = APIRouter(prefix="/api/v1", tags=["diary"])
Member = Annotated[MemberData, Depends(require_member)]
Repository = Annotated[DiaryRepository, Depends(get_diary_repository)]
Storage = Annotated[SupabaseFileStorage, Depends(get_file_storage)]


async def result_response(row: dict, storage: SupabaseFileStorage) -> DiaryResult:
    try:
        signed = await storage.signed_image(row["image_bucket"], row["image_object_key"])
    except StorageSigningError:
        raise AppError(503, "IMAGE_UNAVAILABLE", "이미지를 표시할 수 없습니다.") from None
    return DiaryResult(**row, image_url=signed.url)


@router.get("/summaries/{summary_id}", response_model=ApiSuccess[DiarySummary])
async def summary(summary_id: UUID, member: Member, repository: Repository):
    row = await repository.summary(str(member.id), str(summary_id))
    return ApiSuccess(data=DiarySummary(**row))


@router.post("/diary-images", status_code=201, response_model=ApiSuccess[DiaryResult])
async def generate(
    body: GenerateDiaryInput, member: Member, repository: Repository, storage: Storage,
    ai: Annotated[CodysseyClient, Depends(get_ai_client)],
    image_storage: Annotated[DiaryImageStorage, Depends(get_diary_image_storage)],
):
    summary_row = await repository.prepare_summary(str(member.id), str(body.summary_id))
    try:
        composition = await compose_diary(ai, summary_row)
        data = await ai.generate_image(composition.image_prompt, size=ai.settings.ai_image_size)
        image = await image_storage.upload(data)
    except AIConfigurationError:
        raise AppError(503, "AI_NOT_CONFIGURED", "이미지 생성 설정을 확인해 주세요.") from None
    except (AIRequestError, InvalidDiaryImage):
        raise AppError(502, "IMAGE_GENERATION_FAILED", "이미지를 생성할 수 없습니다. 다시 요청해 주세요.") from None
    except StorageUploadError:
        raise AppError(503, "IMAGE_STORAGE_FAILED", "이미지를 저장할 수 없습니다.") from None
    row = await repository.create_result(str(member.id), str(body.summary_id), composition, image)
    return ApiSuccess(data=await result_response(row, storage))


@router.get("/diary-results/{result_id}", response_model=ApiSuccess[DiaryResult])
async def result(result_id: UUID, member: Member, repository: Repository, storage: Storage):
    row = await repository.result(str(member.id), str(result_id))
    return ApiSuccess(data=await result_response(row, storage))
