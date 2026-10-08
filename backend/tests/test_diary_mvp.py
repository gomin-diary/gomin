import base64
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
import httpx

from app.ai.client import CodysseyClient
from app.ai.dependencies import get_ai_client
from app.api.routes.diary import router
from app.auth.session import require_member
from app.core.errors import AppError
from app.core.exception_handlers import register_exception_handlers
from app.diary.repository import get_diary_repository
from app.schemas.auth import MemberData
from app.storage.dependencies import get_diary_image_storage, get_file_storage
from app.storage.diary_images import DiaryImageStorage
from app.storage.supabase import SignedImage, StoredFile
from test_ai_client import settings
from test_diary_images import encoded_image


class DiaryMvpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.summary_id, self.result_id = str(uuid4()), str(uuid4())
        self.member = MemberData(id=uuid4(), email="member@example.test", name="테스트")
        self.summary = {"id": self.summary_id, "current_feeling": "불안해요",
                        "main_concerns": ["시험"], "emotion_tags": ["불안"]}
        self.row = {"id": self.result_id, "summary_id": self.summary_id, "title": "오늘의 기록",
                    "encouragement_text": "잘 해내고 있어요", "diary_date": "2026-10-08",
                    "image_bucket": "private", "image_object_key": "image.png"}
        self.repository = SimpleNamespace(prepare_summary=AsyncMock(return_value=self.summary),
            summary=AsyncMock(return_value=self.summary), create_result=AsyncMock(return_value=self.row),
            result=AsyncMock(return_value=self.row))
        self.storage = SimpleNamespace(upload=AsyncMock(return_value=StoredFile("private", "image.png")),
            signed_image=AsyncMock(return_value=SignedImage("https://example.test/signed-image", None)))
        self.entry = {"id": str(uuid4()), "source_result_id": self.result_id, "saved_at": "2026-10-08T05:30:00Z"}
        self.repository.save = AsyncMock(return_value=self.entry)
        self.repository.list_entries = AsyncMock(return_value=[{**self.row, "id": self.entry["id"],
            "source_result_id": self.result_id, "emotion_tags": ["불안"]}])
        self.repository.entry = AsyncMock(return_value={**self.row, **self.entry,
            "current_feeling": "불안해요", "main_concerns": ["시험"], "emotion_tags": ["불안"]})
        self.requests = []
        self.fail_image = False
        def provider(request):
            self.requests.append(request)
            if request.url.path == "/v1/chat/completions":
                content = json.dumps({"title": "오늘의 기록", "encouragement_text": "잘 해내고 있어요", "image_prompt": "숲의 동물"})
                return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": content}}]})
            if self.fail_image:
                return httpx.Response(500, text="provider-secret-must-not-leak")
            return httpx.Response(200, json={"result": {"images": [{"b64_json": base64.b64encode(encoded_image()).decode()}]}})
        self.provider = httpx.AsyncClient(transport=httpx.MockTransport(provider))
        self.addAsyncCleanup(self.provider.aclose)
        ai = CodysseyClient(self.provider, settings(ai_api_key="test-only"))
        self.app = FastAPI()
        register_exception_handlers(self.app)
        self.app.include_router(router)
        for dependency, value in [(require_member, self.member), (get_diary_repository, self.repository),
                (get_ai_client, ai), (get_file_storage, self.storage),
                (get_diary_image_storage, DiaryImageStorage(self.storage, ai.settings))]:
            def override(value):
                return lambda: value
            self.app.dependency_overrides[dependency] = override(value)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="https://test")
        self.addAsyncCleanup(self.client.aclose)

    async def test_summary_to_completed_image_runs_inline_and_stores_result(self):
        response = await self.client.post("/api/v1/diary-images", json={"summary_id": self.summary_id})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["data"]["id"], self.result_id)
        self.assertEqual(response.json()["data"]["image_url"], "https://example.test/signed-image")
        self.assertNotIn("image_bucket", response.text)
        self.assertNotIn("job", response.text)
        self.repository.prepare_summary.assert_awaited_once_with(str(self.member.id), self.summary_id)
        self.assertEqual([r.url.path for r in self.requests], ["/v1/chat/completions", "/api/v1/images"])
        self.assertEqual(json.loads(self.requests[1].content)["model"], "gpt-image-2")
        self.assertEqual(self.storage.upload.call_args.args[0], encoded_image())
        self.repository.create_result.assert_awaited_once()

    async def test_other_members_summary_is_rejected_before_paid_request(self):
        self.repository.prepare_summary.side_effect = AppError(404, "NOT_FOUND", "요약을 찾을 수 없습니다.")
        response = await self.client.post("/api/v1/diary-images", json={"summary_id": self.summary_id})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.requests, [])
        self.storage.upload.assert_not_awaited()

    async def test_provider_failure_never_stores_or_exposes_provider_text(self):
        self.fail_image = True
        response = await self.client.post("/api/v1/diary-images", json={"summary_id": self.summary_id})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("provider-secret", response.text)
        self.storage.upload.assert_not_awaited()
        self.repository.create_result.assert_not_awaited()

    async def test_save_returns_entry_and_never_regenerates_image(self):
        for _ in range(2):
            response = await self.client.post(f"/api/v1/diary-results/{self.result_id}/collection-entry")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["data"]["id"], self.entry["id"])
        self.repository.save.assert_awaited_with(str(self.member.id), self.result_id)
        self.assertEqual(self.requests, [])

    async def test_save_cannot_access_another_members_result(self):
        self.repository.save.side_effect = AppError(404, "NOT_FOUND", "기록을 찾을 수 없습니다.")
        response = await self.client.post(f"/api/v1/diary-results/{self.result_id}/collection-entry")
        self.assertEqual(response.status_code, 404)

    async def test_list_returns_owned_entries_and_signed_images(self):
        response = await self.client.get("/api/v1/collection")
        self.assertEqual(response.status_code, 200)
        row = response.json()["data"][0]
        self.assertEqual(row["id"], self.entry["id"])
        self.assertEqual(row["source_result_id"], self.result_id)
        self.assertNotIn("image_bucket", row)
        self.repository.list_entries.assert_awaited_once_with(str(self.member.id))

    async def test_list_empty_is_success(self):
        self.repository.list_entries.return_value = []
        response = await self.client.get("/api/v1/collection")
        self.assertEqual(response.json()["data"], [])
        self.storage.signed_image.assert_not_awaited()

    async def test_generate_save_list_detail_keep_the_same_result_and_original_summary(self):
        generated = await self.client.post("/api/v1/diary-images", json={"summary_id": self.summary_id})
        result_id = generated.json()["data"]["id"]
        saved = await self.client.post(f"/api/v1/diary-results/{result_id}/collection-entry")
        entry_id = saved.json()["data"]["id"]
        listed = (await self.client.get("/api/v1/collection")).json()["data"]
        self.assertEqual(listed[0]["id"], entry_id)
        detail = (await self.client.get(f"/api/v1/collection/{entry_id}")).json()["data"]
        self.assertEqual(detail["source_result_id"], result_id)
        self.assertEqual(detail["summary_id"], self.summary_id)
        self.assertEqual(detail["current_feeling"], self.summary["current_feeling"])
        self.assertEqual(detail["main_concerns"], self.summary["main_concerns"])
        self.assertEqual(detail["emotion_tags"], self.summary["emotion_tags"])
        self.repository.entry.assert_awaited_once_with(str(self.member.id), entry_id)

    async def test_other_members_entry_returns_not_found_without_signing_image(self):
        self.repository.entry.side_effect = AppError(404, "NOT_FOUND", "기록을 찾을 수 없습니다.")
        response = await self.client.get(f"/api/v1/collection/{self.entry['id']}")
        self.assertEqual(response.status_code, 404)
        self.storage.signed_image.assert_not_awaited()
