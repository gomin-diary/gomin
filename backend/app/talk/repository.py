from fastapi import Depends
from postgrest.exceptions import APIError
from supabase import AsyncClient
from typing import Annotated

from app.core.errors import AppError
from app.db.client import get_supabase


ERRORS = {
    "TALK_NOT_FOUND": (404, "NOT_FOUND", "대화 또는 요약을 찾을 수 없어요."),
    "TALK_BUSY": (409, "TALK_BUSY", "진행 중인 응답이나 요약을 기다려 주세요."),
    "TALK_EMPTY": (409, "TALK_EMPTY", "메시지를 먼저 보내 주세요."),
    "TALK_CONFLICT": (409, "CONFLICT", "요청 정보가 저장된 내용과 달라요."),
    "TALK_STALE_SUMMARY": (409, "STALE_SUMMARY", "대화가 추가되었어요. 다시 이야기하기로 돌아가 새 요약을 확인해 주세요."),
    "TALK_INVALID_INPUT": (422, "VALIDATION_ERROR", "공백을 포함해 1~100자의 메시지를 입력해 주세요."),
}


class TalkRepository:
    def __init__(self, database: AsyncClient):
        self.database = database

    async def execute(self, query):
        try:
            return (await query.execute()).data
        except APIError as error:
            if error.message in ERRORS:
                raise AppError(*ERRORS[error.message]) from None
            raise AppError(503, "SERVICE_UNAVAILABLE", "대화 저장 서비스를 이용할 수 없어요.") from None
        except Exception:
            raise AppError(503, "SERVICE_UNAVAILABLE", "대화 저장 서비스를 이용할 수 없어요.") from None

    async def rpc(self, name, member_id, conversation_id, **params):
        return await self.execute(self.database.rpc(name, {
            "p_member_id": str(member_id), "p_conversation_id": str(conversation_id), **params,
        }))

    async def create(self, member_id):
        rows = await self.execute(self.database.table("conversations").insert({"member_id": str(member_id)}))
        return await self.snapshot(member_id, rows[0]["id"])

    async def snapshot(self, member_id, conversation_id):
        return await self.rpc("gomin_talk_snapshot", member_id, conversation_id)

    async def send(self, member_id, conversation_id, payload):
        return await self.rpc("gomin_talk_send", member_id, conversation_id,
                              p_client_message_id=str(payload.client_message_id), p_content=payload.content)

    async def start_summary(self, member_id, conversation_id, request_id):
        return await self.rpc("gomin_talk_start_summary", member_id, conversation_id, p_request_id=str(request_id))

    async def complete(self, member_id, conversation_id, job, output=None, error_code=None):
        return await self.rpc("gomin_talk_complete", member_id, conversation_id,
                              p_job_id=job["id"], p_lease_token=job["lease_token"],
                              p_output=output, p_error_code=error_code)

    async def resume(self, member_id, conversation_id):
        await self.rpc("gomin_talk_resume", member_id, conversation_id)
        return await self.snapshot(member_id, conversation_id)

    async def confirm(self, member_id, conversation_id, summary_id):
        return await self.rpc("gomin_talk_confirm", member_id, conversation_id, p_summary_id=str(summary_id))

    async def confirmed_summary(self, member_id, conversation_id, summary_id):
        # Scope all three identifiers even though the server uses a privileged SDK.
        rows = await self.execute(self.database.table("conversation_summaries").select("*")
                                  .eq("member_id", str(member_id)).eq("conversation_id", str(conversation_id))
                                  .eq("id", str(summary_id)).limit(1))
        if not rows:
            raise AppError(404, "NOT_FOUND", "요약을 찾을 수 없어요.")
        if rows[0]["confirmed_at"] is None:
            raise AppError(409, "SUMMARY_NOT_CONFIRMED", "확정된 요약만 다음 단계에 전달할 수 있어요.")
        return rows[0]


def get_talk_repository(database: Annotated[AsyncClient, Depends(get_supabase)]) -> TalkRepository:
    return TalkRepository(database)
