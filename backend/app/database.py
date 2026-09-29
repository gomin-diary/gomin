from fastapi import Request
from httpx import AsyncClient as AsyncHttpClient
from supabase import AsyncClient, AsyncClientOptions, acreate_client

from app.config import Settings


async def create_supabase_client(
    settings: Settings, http_client: AsyncHttpClient
) -> AsyncClient:
    return await acreate_client(
        str(settings.supabase_url).rstrip("/"),
        settings.supabase_secret_key.get_secret_value(),
        options=AsyncClientOptions(
            auto_refresh_token=False,
            persist_session=False,
            httpx_client=http_client,
        ),
    )


def get_supabase(request: Request) -> AsyncClient:
    return request.app.state.supabase
