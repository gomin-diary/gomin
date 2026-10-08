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
