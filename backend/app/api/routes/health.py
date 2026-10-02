from fastapi import APIRouter, Depends
from httpx import HTTPError
from postgrest.exceptions import APIError
from supabase import AsyncClient

from app.core.errors import AppError
from app.db.client import get_supabase
from app.schemas.response import ApiSuccess, DatabaseHealthData, HealthData

router = APIRouter()


@router.get("/api/v1/health", response_model=ApiSuccess[HealthData])
async def health() -> ApiSuccess[HealthData]:
    return ApiSuccess(data=HealthData())


@router.get("/api/v1/health/db", response_model=ApiSuccess[DatabaseHealthData])
async def database_health(
    supabase: AsyncClient = Depends(get_supabase),
) -> ApiSuccess[DatabaseHealthData]:
    try:
        result = await supabase.rpc("health_check").execute()
    except (APIError, HTTPError) as exc:
        raise AppError(503, "SERVICE_UNAVAILABLE", "서비스를 일시적으로 이용할 수 없습니다.") from exc
    if result.data is not True:
        raise AppError(503, "SERVICE_UNAVAILABLE", "서비스를 일시적으로 이용할 수 없습니다.")
    return ApiSuccess(data=DatabaseHealthData())
