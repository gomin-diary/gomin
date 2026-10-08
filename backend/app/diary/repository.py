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
                raise AppError(404, "NOT_FOUND", "기록을 찾을 수 없습니다.") from None
            if error.code == "23514":
                raise AppError(409, "SUMMARY_CHANGED", "최신 요약을 확인한 뒤 다시 요청해 주세요.") from None
            raise AppError(503, "SERVICE_UNAVAILABLE", "기록을 처리할 수 없습니다.") from None
        except Exception:
            raise AppError(503, "SERVICE_UNAVAILABLE", "기록을 처리할 수 없습니다.") from None

    async def summary(self, member_id: str, summary_id: str):
        rows = await self.execute(self.database.table("conversation_summaries").select(
            "id,current_feeling,main_concerns,emotion_tags"
        ).eq("id", summary_id).eq("member_id", member_id).limit(1))
        if not rows:
            raise AppError(404, "NOT_FOUND", "요약을 찾을 수 없습니다.")
        return rows[0]

    async def prepare_summary(self, member_id: str, summary_id: str):
        return await self.execute(self.database.rpc("prepare_diary_summary", {
            "p_member_id": member_id, "p_summary_id": summary_id,
        }))

    async def create_result(self, member_id: str, summary_id: str, composition, image):
        return await self.execute(self.database.rpc("create_diary_result", {
            "p_member_id": member_id, "p_summary_id": summary_id,
            "p_title": composition.title, "p_encouragement_text": composition.encouragement_text,
            "p_image_bucket": image.bucket, "p_image_object_key": image.path,
        }))

    async def result(self, member_id: str, result_id: str):
        return await self.execute(self.database.rpc("get_diary_result", {
            "p_member_id": member_id, "p_result_id": result_id,
        }))

    async def save(self, member_id: str, result_id: str):
        return await self.execute(self.database.rpc("save_collection_result", {
            "p_member_id": member_id, "p_result_id": result_id,
        }))

    async def list_entries(self, member_id: str):
        return await self.execute(self.database.rpc("get_collection_entries", {"p_member_id": member_id}))


def get_diary_repository(database: Annotated[AsyncClient, Depends(get_supabase)]):
    return DiaryRepository(database)
