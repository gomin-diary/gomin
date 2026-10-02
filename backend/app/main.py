from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient as AsyncHttpClient, Timeout

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.signup import router as signup_router
from app.core.config import get_settings
from app.core.exception_handlers import ERROR_RESPONSES, register_exception_handlers
from app.db.client import create_supabase_client

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

app.include_router(health_router)

app.include_router(auth_router)
app.include_router(signup_router)
