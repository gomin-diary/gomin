from collections.abc import AsyncIterator
import asyncio
from contextlib import suppress
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient as AsyncHttpClient, Timeout

from app.ai.client import CodysseyClient
from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.signup import router as signup_router
from app.api.routes.google_oauth import router as google_oauth_router
from app.api.routes.diary import router as diary_router
from app.auth.google_provider import GoogleProvider
from app.core.config import get_settings
from app.core.exception_handlers import ERROR_RESPONSES, register_exception_handlers
from app.db.client import create_supabase_client
from app.diary.repository import DiaryRepository
from app.diary.worker import DiaryWorker
from app.storage.diary_images import DiaryImageStorage
from app.storage.supabase import SupabaseFileStorage

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with AsyncHttpClient(timeout=Timeout(10, connect=5)) as http_client:
        app.state.supabase = await create_supabase_client(settings, http_client)
        app.state.google_provider = GoogleProvider(http_client, settings)
        app.state.ai_client = CodysseyClient(http_client, settings)
        worker_task = None
        if settings.diary_worker_enabled:
            storage_settings = settings.model_copy(update={"storage_bucket": settings.diary_image_bucket})
            worker = DiaryWorker(DiaryRepository(app.state.supabase), app.state.ai_client,
                DiaryImageStorage(SupabaseFileStorage(app.state.supabase, storage_settings), settings))
            worker_task = asyncio.create_task(worker.run())
        try:
            yield
        finally:
            if worker_task:
                worker_task.cancel()
                with suppress(asyncio.CancelledError):
                    await worker_task


app = FastAPI(title="Gomin API", version="0.1.0", lifespan=lifespan, responses=ERROR_RESPONSES)
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(health_router)

app.include_router(sessions_router)
app.include_router(auth_router)
app.include_router(signup_router)

app.include_router(google_oauth_router)
app.include_router(diary_router)
