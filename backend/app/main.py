from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from psycopg import Error as DatabaseError
from psycopg_pool import PoolTimeout

from app.config import get_settings
from app.database import create_pool

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    pool = create_pool(settings.database_url.get_secret_value())
    app.state.db_pool = pool
    try:
        await pool.open(wait=True, timeout=10)
        yield
    finally:
        await pool.close()


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
async def database_health(request: Request) -> dict[str, str]:
    try:
        async with request.app.state.db_pool.connection() as connection:
            await connection.execute("SELECT 1")
    except (DatabaseError, PoolTimeout) as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "database": "connected"}
