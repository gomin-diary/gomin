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

    async def claim_image(self, job_id: str | None = None):
        return await self.rpc("claim_diary_image", {"p_job_id": job_id})

    async def expire_image_leases(self):
        return await self.rpc("expire_diary_image_leases", {})

    async def finalize_image(self, job_id: str, lease_token: str, title: str,
                             encouragement: str, bucket: str, path: str):
        return await self.rpc("finalize_diary_image", {
            "p_job_id": job_id, "p_lease_token": lease_token, "p_title": title,
            "p_encouragement_text": encouragement, "p_image_bucket": bucket,
            "p_image_object_key": path,
        })

    async def fail_image(self, job_id: str, lease_token: str, error_code: str):
        return await self.rpc("fail_diary_image", {
            "p_job_id": job_id, "p_lease_token": lease_token, "p_error_code": error_code,
        })

    async def image_summary(self, job: dict):
        rows = await self.execute(self.database.table("conversation_summaries")
            .select("current_feeling,main_concerns,emotion_tags,confirmed_at")
            .eq("id", job["input_summary_id"]).eq("member_id", job["member_id"])
            .eq("conversation_id", job["conversation_id"]).limit(1))
        if not rows or rows[0]["confirmed_at"] is None:
            raise AppError(409, "CONFLICT", "확정한 요약을 찾을 수 없습니다.")
        return rows[0]


def get_diary_repository(database: Annotated[AsyncClient, Depends(get_supabase)]) -> DiaryRepository:
    return DiaryRepository(database)
