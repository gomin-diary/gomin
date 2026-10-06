from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.auth.session import require_member
from app.core.config import Settings
from app.core.errors import AppError
from app.schemas.auth import MemberData
from app.schemas.files import UploadUrlData, UploadUrlInput
from app.schemas.response import ApiSuccess
from app.storage.dependencies import get_file_storage, get_storage_settings
from app.storage.supabase import StorageSigningError, SupabaseFileStorage

router = APIRouter(prefix="/api/v1/files", tags=["files"])


@router.post("/upload-url", response_model=ApiSuccess[UploadUrlData])
async def create_upload_url(
    payload: UploadUrlInput, request: Request, response: Response,
    member: Annotated[MemberData, Depends(require_member)],
    settings: Annotated[Settings, Depends(get_storage_settings)],
    storage: Annotated[SupabaseFileStorage, Depends(get_file_storage)],
) -> ApiSuccess[UploadUrlData]:
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.cors_origins:
        raise AppError(403, "FORBIDDEN", "허용되지 않은 요청 출처입니다.")
    if payload.size > settings.storage_max_file_size_bytes:
        raise AppError(413, "FILE_TOO_LARGE", "업로드 가능한 파일 크기를 초과했습니다.")
    try:
        grant = await storage.create_upload_url(member.id)
    except StorageSigningError:
        raise AppError(503, "STORAGE_UNAVAILABLE", "파일 업로드를 준비하지 못했습니다. 잠시 후 다시 시도해 주세요.") from None
    response.headers["Cache-Control"] = "no-store"
    return ApiSuccess(data=UploadUrlData(
        bucket=grant.bucket, path=grant.path, upload_url=grant.upload_url,
        expires_in=grant.expires_in, max_file_size_bytes=settings.storage_max_file_size_bytes,
    ))
