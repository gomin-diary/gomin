from typing import Annotated

from fastapi import Depends
from supabase import AsyncClient

from app.core import config
from app.core.config import Settings
from app.db.client import get_supabase
from app.storage.supabase import SupabaseFileStorage


def get_storage_settings() -> Settings:
    return config.get_settings()


def get_file_storage(
    client: Annotated[AsyncClient, Depends(get_supabase)],
    settings: Annotated[Settings, Depends(get_storage_settings)],
) -> SupabaseFileStorage:
    return SupabaseFileStorage(client, settings)
