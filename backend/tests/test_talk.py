import unittest
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes.talk import router
from app.auth.security import token_digest
from app.auth.session import COOKIE_NAME, get_auth_repository, get_auth_settings
from app.core.config import Settings
from app.core.errors import AppError
from app.core.exception_handlers import ERROR_RESPONSES, register_exception_handlers
from app.schemas.talk import MessageInput, SummaryContent
from app.talk.provider import UnconfiguredTalkProvider, get_talk_provider
from app.talk.repository import get_talk_repository
from app.talk.service import generate


def now():
    return datetime.now(timezone.utc).isoformat()


class Repository:
    """API-isolated fixture only. Atomic SQL is covered by talk-mvp.test.mjs."""
    def __init__(self):
        self.conversations = {}
        self.job_records = {}
        self.fail = False

    def owned(self, member_id, conversation_id):
        if self.fail:
            raise AppError(503, "SERVICE_UNAVAILABLE", "저장 서비스 오류")
        value = self.conversations.get(str(conversation_id))
        if not value or value["owner"] != str(member_id):
            raise AppError(404, "NOT_FOUND", "대화 없음")
        return value

    async def create(self, member_id):
        value = dict(id=str(uuid4()), owner=str(member_id), phase="chatting", messages=[], summaries=[], jobs=[])
        self.conversations[value["id"]] = value
        return deepcopy(value)

    async def snapshot(self, member_id, conversation_id):
        return deepcopy(self.owned(member_id, conversation_id))

    def job(self, value, kind, boundary):
        job = dict(id=str(uuid4()), kind=kind, status="running", source_until_seq_no=boundary, error_code=None, lease_token=str(uuid4()))
        value["jobs"].append(job)
        self.job_records[job["id"]] = job
        return deepcopy(job)

    async def send(self, member_id, conversation_id, payload):
        value = self.owned(member_id, conversation_id)
        message = dict(id=str(uuid4()), conversation_id=value["id"], seq_no=len(value["messages"])+1,
                       role="user", content=payload.content, created_at=now())
        value["messages"].append(message)
        return dict(message=message, job=self.job(value, "reply", message["seq_no"]), execute=True)

    async def start_summary(self, member_id, conversation_id, request_id):
        value = self.owned(member_id, conversation_id)
        value["phase"] = "summarizing"
        return dict(job=self.job(value, "summary", len(value["messages"])), execute=True)

    async def complete(self, member_id, conversation_id, job, output=None, error_code=None):
        value = self.owned(member_id, conversation_id)
        record = self.job_records[job["id"]]
        record["status"] = "failed" if error_code else "succeeded"
        record["error_code"] = error_code
        if error_code:
            return
        if job["kind"] == "reply":
            value["messages"].append(dict(id=str(uuid4()), conversation_id=value["id"], seq_no=len(value["messages"])+1,
                                          role="assistant", content=output["content"], created_at=now()))
        else:
            value["summaries"].append(dict(id=str(uuid4()), conversation_id=value["id"], version=len(value["summaries"])+1,
                                          member_id=value["owner"], generation_job_id=job["id"],
                                          source_until_seq_no=job["source_until_seq_no"], confirmed_at=None, created_at=now(), **output))
            value["phase"] = "reviewing"

    async def resume(self, member_id, conversation_id):
        value = self.owned(member_id, conversation_id); value["phase"] = "chatting"
        return deepcopy(value)

    async def confirm(self, member_id, conversation_id, summary_id):
        value = self.owned(member_id, conversation_id)
        summary = next((s for s in value["summaries"] if s["id"] == str(summary_id)), None)
        if not summary:
            raise AppError(404, "NOT_FOUND", "요약 없음")
        summary["confirmed_at"] = summary["confirmed_at"] or now()
        return deepcopy(summary)

    async def confirmed_summary(self, member_id, conversation_id, summary_id):
        value = self.owned(member_id, conversation_id)
        summary = next((s for s in value["summaries"] if s["id"] == str(summary_id)), None)
        if not summary:
            raise AppError(404, "NOT_FOUND", "요약 없음")
        if summary["confirmed_at"] is None:
            raise AppError(409, "SUMMARY_NOT_CONFIRMED", "미확정 요약")
        return deepcopy(summary)


class TalkApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.member = dict(id=str(uuid4()), email="owner@example.test", name="테스트")
        self.token = "a"*43
        self.auth = AsyncMock()
        self.auth.renew_session.side_effect = lambda digest: self.member if digest == token_digest(self.token) else None
        self.repository = Repository()
        self.provider = AsyncMock()
        self.provider.reply.return_value = "지난 이야기에 이어, 어떤 마음이 들었어?"
        self.provider.summarize.return_value = SummaryContent(current_feeling="긴장돼요", main_concerns=["시험"], emotion_tags=["불안"])
        settings = Settings(_env_file=None, supabase_url="https://example.supabase.co", supabase_secret_key="test-placeholder", auth_cookie_secure=False)
        app = FastAPI(responses=ERROR_RESPONSES); register_exception_handlers(app); app.include_router(router)
        app.dependency_overrides[get_auth_repository] = lambda: self.auth
        app.dependency_overrides[get_auth_settings] = lambda: settings
        app.dependency_overrides[get_talk_repository] = lambda: self.repository
        app.dependency_overrides[get_talk_provider] = lambda: self.provider
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies={COOKIE_NAME: self.token})

    async def asyncTearDown(self):
        await self.client.aclose()

    async def create(self):
        response = await self.client.post("/api/v1/conversations")
        self.assertEqual(response.status_code, 201)
        return response.json()["data"]["id"]

    async def send(self, conversation_id, content="시험이 불안해요"):
        return await self.client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": content, "client_message_id": str(uuid4())})

    async def summary(self, conversation_id):
        response = await self.client.post(f"/api/v1/conversations/{conversation_id}/summaries", json={"request_id": str(uuid4())})
        self.assertEqual(response.status_code, 202)
        return (await self.client.get(f"/api/v1/conversations/{conversation_id}")).json()["data"]["summaries"][-1]

    async def test_requires_real_shared_session_dependency_on_every_route(self):
        conversation_id = await self.create(); summary_id = str(uuid4())
        self.client.cookies.clear()
        operations = [("POST", "", None), ("GET", f"/{conversation_id}", None),
                      ("POST", f"/{conversation_id}/messages", {"content": "원문", "client_message_id": str(uuid4())}),
                      ("POST", f"/{conversation_id}/summaries", {"request_id": str(uuid4())}),
                      ("POST", f"/{conversation_id}/resume", None),
                      ("POST", f"/{conversation_id}/summaries/{summary_id}/confirm", None),
                      ("GET", f"/{conversation_id}/summaries/{summary_id}/handoff", None)]
        for method, path, body in operations:
            response = await self.client.request(method, "/api/v1/conversations"+path, json=body)
            self.assertEqual(response.status_code, 401)
            self.assertFalse(response.json()["success"])

    async def test_other_member_cannot_read_send_summarize_resume_confirm_or_handoff(self):
        conversation_id = await self.create(); await self.send(conversation_id); summary = await self.summary(conversation_id)
        self.member = {**self.member, "id": str(uuid4())}
        root = f"/api/v1/conversations/{conversation_id}"
        for method, path, body in [("GET", "", None), ("POST", "/messages", {"content": "타인", "client_message_id": str(uuid4())}),
                                  ("POST", "/summaries", {"request_id": str(uuid4())}), ("POST", "/resume", None),
                                  ("POST", f"/summaries/{summary['id']}/confirm", None), ("GET", f"/summaries/{summary['id']}/handoff", None)]:
            response = await self.client.request(method, root+path, json=body)
            self.assertEqual(response.status_code, 404)

    async def test_boundaries_and_private_validation(self):
        conversation_id = await self.create()
        for content in ("", " \n\t", "가"*101):
            response = await self.send(conversation_id, content)
            self.assertEqual(response.status_code, 422)
            self.assertFalse(response.json()["success"])
        content = "가"*98+" \n"; response = await self.send(conversation_id, content)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["data"]["message"]["content"], content)
        response = await self.client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": "내용", "client_message_id": str(uuid4()), "member_id": str(uuid4())})
        self.assertEqual(response.status_code, 422)

    async def test_context_restoration_summary_and_confirmed_server_handoff(self):
        conversation_id = await self.create(); await self.send(conversation_id, "첫 고민"); await self.send(conversation_id, "추가 고민")
        messages = (await self.client.get(f"/api/v1/conversations/{conversation_id}")).json()["data"]["messages"]
        self.assertEqual([m["seq_no"] for m in messages], [1, 2, 3, 4])
        self.assertEqual([m["content"] for m in self.provider.reply.call_args.args[0]], ["첫 고민", self.provider.reply.return_value, "추가 고민"])
        summary = await self.summary(conversation_id)
        root = f"/api/v1/conversations/{conversation_id}/summaries/{summary['id']}"
        self.assertEqual((await self.client.get(root+"/handoff")).status_code, 409)
        handoff = (await self.client.post(root+"/confirm")).json()["data"]
        self.assertTrue(handoff["confirmed"]); self.assertEqual(handoff["summary_id"], summary["id"])
        self.assertNotIn("member_id", handoff["summary"])
        self.assertNotIn("generation_job_id", handoff["summary"])
        self.assertEqual(handoff["next_stage_status"], "not_started")
        self.assertEqual((await self.client.get(root+"/handoff")).json()["data"], handoff)
        self.assertEqual((await self.client.get(f"/api/v1/conversations/{conversation_id}")).json()["data"]["messages"], messages)

    async def test_provider_failures_never_create_fake_reply_or_summary(self):
        conversation_id = await self.create(); self.provider.reply.side_effect = RuntimeError("private-provider-error")
        await self.send(conversation_id)
        self.provider.summarize.side_effect = TimeoutError()
        await self.client.post(f"/api/v1/conversations/{conversation_id}/summaries", json={"request_id": str(uuid4())})
        response = await self.client.get(f"/api/v1/conversations/{conversation_id}"); data = response.json()["data"]
        self.assertEqual(len(data["messages"]), 1); self.assertEqual(data["summaries"], [])
        self.assertEqual([j["error_code"] for j in data["jobs"]], ["AI_FAILED", "AI_TIMEOUT"])
        self.assertNotIn("private-provider-error", response.text)

    async def test_database_failure_is_common_error_not_success(self):
        conversation_id = await self.create(); self.repository.fail = True
        response = await self.client.get(f"/api/v1/conversations/{conversation_id}")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["data"], None)


class GenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_source_filter_excludes_later_messages_and_invalid_ai_output(self):
        repository, provider = AsyncMock(), AsyncMock()
        repository.snapshot.return_value = {"messages": [dict(role="user", content="저장 원문", seq_no=1), dict(role="user", content="범위 밖 원문", seq_no=2)]}
        job = dict(id=str(uuid4()), kind="summary", source_until_seq_no=1, lease_token=str(uuid4()))
        provider.summarize.return_value = {"current_feeling": "", "main_concerns": [], "emotion_tags": []}
        await generate(repository, provider, uuid4(), uuid4(), job)
        self.assertEqual(provider.summarize.call_args.args[0], [{"role": "user", "content": "저장 원문"}])
        self.assertEqual(repository.complete.call_args.args[-1], "AI_FAILED")

    async def test_unconfigured_provider_fails_explicitly_without_production_mock(self):
        repository = AsyncMock(); repository.snapshot.return_value = {"messages": []}
        job = dict(id=str(uuid4()), kind="reply", source_until_seq_no=1, lease_token=str(uuid4()))
        await generate(repository, UnconfiguredTalkProvider(), uuid4(), uuid4(), job)
        self.assertEqual(repository.complete.call_args.args[-1], "AI_NOT_CONFIGURED")
