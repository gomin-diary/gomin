from datetime import datetime, timezone
from uuid import uuid4
import unittest
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.diary import router
from app.auth.session import require_member
from app.core.exception_handlers import register_exception_handlers
from app.diary.repository import get_diary_repository
from app.schemas.auth import MemberData
from app.storage.dependencies import get_storage_settings
from test_ai_client import settings


class DiaryAPITests(unittest.TestCase):
    def setUp(self):
        self.member = MemberData(id=uuid4(), email="test@example.test", name="test")
        self.conversation_id, self.summary_id, self.key = uuid4(), uuid4(), uuid4()
        self.repository = AsyncMock()
        self.repository.rpc.return_value = {
            "id": str(uuid4()), "conversation_id": str(self.conversation_id),
            "input_summary_id": str(self.summary_id), "status": "queued", "attempt_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(), "lease_token": str(uuid4()),
            "request_fingerprint": "private", "member_id": str(self.member.id),
        }
        self.app = FastAPI()
        register_exception_handlers(self.app)
        self.app.include_router(router)
        self.app.dependency_overrides[require_member] = lambda: self.member
        self.app.dependency_overrides[get_diary_repository] = lambda: self.repository
        self.app.dependency_overrides[get_storage_settings] = lambda: settings(ai_image_model="image-test")
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def post(self, **extra):
        return self.client.post(f"/api/v1/conversations/{self.conversation_id}/image-jobs", json={
            "summary_id": str(self.summary_id), "idempotency_key": str(self.key), **extra})

    def test_session_identity_fingerprint_and_public_job_contract(self):
        response = self.post()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertNotIn("lease_token", response.text)
        self.assertNotIn("request_fingerprint", response.text)
        args = self.repository.rpc.call_args.args[1]
        self.assertEqual(args["p_member_id"], str(self.member.id))
        self.assertEqual(args["p_text_model"], "gpt-5.4-mini")
        fingerprint = args["p_fingerprint"]
        self.post()
        self.assertEqual(self.repository.rpc.call_args.args[1]["p_fingerprint"], fingerprint)
        self.app.dependency_overrides[get_storage_settings] = lambda: settings(ai_image_model="changed")
        self.post()
        self.assertNotEqual(self.repository.rpc.call_args.args[1]["p_fingerprint"], fingerprint)

    def test_rejects_client_ownership_or_summary_text_and_missing_model(self):
        self.assertEqual(self.post(member_id=str(uuid4())).status_code, 422)
        self.assertEqual(self.post(current_feeling="untrusted").status_code, 422)
        self.repository.rpc.assert_not_awaited()
        self.app.dependency_overrides[get_storage_settings] = lambda: settings()
        self.assertEqual(self.post().status_code, 503)
        self.repository.rpc.assert_not_awaited()

    def test_save_passes_only_session_member_and_result_id_and_returns_original_entry(self):
        result_id = uuid4()
        entry = {"id": str(uuid4()), "source_result_id": str(result_id),
                 "saved_at": datetime.now(timezone.utc).isoformat(), "member_id": str(self.member.id)}
        self.repository.rpc.return_value = entry
        first = self.client.post(f"/api/v1/diary-results/{result_id}/collection-entry")
        second = self.client.post(f"/api/v1/diary-results/{result_id}/collection-entry")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertNotIn("member_id", first.text)
        self.repository.rpc.assert_awaited_with("save_collection_result", {
            "p_member_id": str(self.member.id), "p_result_id": str(result_id),
        })

    def test_list_cursor_is_stable_and_passes_only_session_owner(self):
        row = {"id": str(uuid4()), "source_result_id": str(uuid4()), "summary_id": str(self.summary_id),
               "conversation_id": str(self.conversation_id), "title": "오늘", "diary_date": "2026-10-08",
               "emotion_tags": ["불안"], "saved_at": "2026-10-08T12:34:56.123456+00:00",
               "image_bucket": "private", "image_object_key": "private-path"}
        self.repository.rpc.return_value = [row, {**row, "id": str(uuid4())}]
        response = self.client.get("/api/v1/collection?limit=1&emotion=불안")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("image_object_key", response.text)
        cursor = response.json()["data"]["next_cursor"]
        self.client.get("/api/v1/collection", params={"limit": 1, "cursor": cursor})
        params = self.repository.rpc.call_args.args[1]
        self.assertEqual(params["p_member_id"], str(self.member.id))
        self.assertEqual(params["p_after_id"], row["id"])
        self.assertEqual(params["p_after_saved_at"], row["saved_at"])
        self.assertEqual(self.client.get("/api/v1/collection?cursor=bad").status_code, 422)
        self.repository.rpc.return_value = []
        empty = self.client.get("/api/v1/collection").json()["data"]
        self.assertEqual(empty, {"items": [], "next_cursor": None})

    def test_detail_keeps_source_summary_order_and_excludes_storage_paths(self):
        row = {"id": str(uuid4()), "source_result_id": str(uuid4()), "summary_id": str(self.summary_id),
               "conversation_id": str(self.conversation_id), "title": "기록", "diary_date": "2026-10-08",
               "saved_at": "2026-10-08T12:34:56+00:00", "completed_at": "2026-10-08T12:30:00+00:00",
               "encouragement_text": "괜찮아요", "current_feeling": "걱정", "main_concerns": ["두번째", "첫번째"],
               "emotion_tags": ["불안", "슬픔"], "image_bucket": "private", "image_object_key": "private-path"}
        self.repository.rpc.return_value = row
        response = self.client.get(f"/api/v1/collection/{row['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["main_concerns"], ["두번째", "첫번째"])
        self.assertNotIn("image_object_key", response.text)
        self.repository.rpc.assert_awaited_with("get_collection_entry", {
            "p_member_id": str(self.member.id), "p_entry_id": row["id"],
        })

    def test_job_query_excludes_internal_tokens_and_returns_no_incomplete_result(self):
        row = {**self.repository.rpc.return_value, "result": None}
        self.repository.rpc.return_value = row
        response = self.client.get(f"/api/v1/image-jobs/{row['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"]["result"])
        self.assertNotIn("lease_token", response.text)
        self.repository.rpc.assert_awaited_with("get_diary_image_job", {
            "p_member_id": str(self.member.id), "p_job_id": row["id"],
        })
