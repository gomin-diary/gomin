from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient as AsyncHttpClient, HTTPError, Timeout
from postgrest.exceptions import APIError
from supabase import AsyncClient

from app.config import get_settings
from app.database import create_supabase_client, get_supabase

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with AsyncHttpClient(timeout=Timeout(10, connect=5)) as http_client:
        app.state.supabase = await create_supabase_client(settings, http_client)
        yield


app = FastAPI(title="Gomin API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health/db")
async def database_health(
    supabase: AsyncClient = Depends(get_supabase),
) -> dict[str, str]:
    try:
        result = await supabase.rpc("health_check").execute()
    except (APIError, HTTPError) as exc:
        raise HTTPException(status_code=503, detail="Supabase unavailable") from exc
    if result.data is not True:
        raise HTTPException(status_code=503, detail="Supabase unavailable")
    return {"status": "ok", "database": "connected"}
