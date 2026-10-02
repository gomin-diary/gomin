from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient as AsyncHttpClient, HTTPError, Timeout
from postgrest.exceptions import APIError
from supabase import AsyncClient

from app.config import get_settings
from app.database import create_supabase_client, get_supabase
from app.errors import AppError
from app.exception_handlers import ERROR_RESPONSES, register_exception_handlers
from app.schemas.response import ApiSuccess, DatabaseHealthData, HealthData

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with AsyncHttpClient(timeout=Timeout(10, connect=5)) as http_client:
        app.state.supabase = await create_supabase_client(settings, http_client)
        yield


app = FastAPI(title="Gomin API", version="0.1.0", lifespan=lifespan, responses=ERROR_RESPONSES)
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/api/v1/health", response_model=ApiSuccess[HealthData])
async def health() -> ApiSuccess[HealthData]:
    return ApiSuccess(data=HealthData())


@app.get("/api/v1/health/db", response_model=ApiSuccess[DatabaseHealthData])
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
