from typing import Annotated

from fastapi import Depends
from postgrest.exceptions import APIError
from supabase import AsyncClient

from app.core.errors import AppError
from app.db.client import get_supabase


class DiaryRepository:
    def __init__(self, database: AsyncClient):
        self.database = database

    async def execute(self, query):
        try:
            return (await query.execute()).data
        except APIError as error:
            if error.code == "P0002":
                raise AppError(404, "NOT_FOUND", "요청한 기록을 찾을 수 없습니다.") from None
            if error.code in ("P0001", "23505", "23514"):
                raise AppError(409, "CONFLICT", "기록의 현재 상태와 요청이 충돌합니다.") from None
            raise AppError(503, "SERVICE_UNAVAILABLE", "기록 서비스를 일시적으로 이용할 수 없습니다.") from None
        except Exception:
            raise AppError(503, "SERVICE_UNAVAILABLE", "기록 서비스를 일시적으로 이용할 수 없습니다.") from None

    async def rpc(self, name: str, params: dict):
        return await self.execute(self.database.rpc(name, params))


def get_diary_repository(database: Annotated[AsyncClient, Depends(get_supabase)]) -> DiaryRepository:
    return DiaryRepository(database)
