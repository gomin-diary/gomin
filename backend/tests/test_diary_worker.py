import asyncio
import base64
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.ai.client import CodysseyClient
from app.diary.worker import DiaryWorker
from app.storage.supabase import StorageUploadError
from test_ai_client import settings
from test_diary_images import encoded_image


class DiaryWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_whole_pipeline_uses_recorded_models_and_only_finalizes_after_upload(self):
        seen = []
        def handler(request):
            body = json.loads(request.content)
            seen.append(body)
            if request.url.path == '/v1/chat/completions':
                return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
                    "role": "assistant", "content": json.dumps({"title": "시험 앞의 마음",
                    "encouragement_text": "천천히 준비해도 괜찮아요", "image_prompt": "숲 속 토끼"})}}]})
            return httpx.Response(200, json={"result": {"images": [{"b64_json": base64.b64encode(encoded_image()).decode()}]}})
        repo, storage = AsyncMock(), AsyncMock()
        repo.image_summary.return_value = {"current_feeling": "불안", "main_concerns": ["시험"], "emotion_tags": ["불안"]}
        storage.upload.return_value = SimpleNamespace(bucket="private", path="stored-object")
        job = {"id": "job", "lease_token": "current", "options": {
            "text_model": "recorded-text", "image_model": "recorded-image", "image_size": "1024x1024", "prompt_version": "diary-v1"}}
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            worker = DiaryWorker(repo, CodysseyClient(http_client, settings(ai_api_key="test-only", ai_image_model="changed")), storage)
            await worker.process(job)
        self.assertEqual([r["model"] for r in seen], ["recorded-text", "recorded-image"])
        repo.finalize_image.assert_awaited_once_with("job", "current", "시험 앞의 마음", "천천히 준비해도 괜찮아요", "private", "stored-object")
        repo.fail_image.assert_not_awaited()
        storage.upload.assert_awaited_once()

    async def test_cancellation_leaves_lease_for_expiry(self):
        repo = AsyncMock()
        repo.image_summary.side_effect = asyncio.CancelledError()
        worker = DiaryWorker(repo, None, None)
        job = {"id": "job", "lease_token": "current"}
        with self.assertRaises(asyncio.CancelledError):
            await worker.process(job)
        repo.fail_image.assert_not_awaited()
        repo.finalize_image.assert_not_awaited()

    async def test_unexpected_error_is_stored_only_as_safe_code(self):
        repo = AsyncMock()
        repo.image_summary.side_effect = RuntimeError("private provider text")
        worker = DiaryWorker(repo, None, None)
        await worker.process({"id": "job", "lease_token": "current"})
        repo.fail_image.assert_awaited_once_with("job", "current", "INTERNAL_ERROR")
        repo.finalize_image.assert_not_awaited()

    async def test_upload_failure_and_lost_commit_response_do_not_recall_the_provider(self):
        for failure_stage, code in [('upload', 'STORAGE_FAILED'), ('finalize', 'INTERNAL_ERROR')]:
            repo, storage, provider = AsyncMock(), AsyncMock(), AsyncMock()
            provider.generate_image.return_value = encoded_image()
            storage.upload.return_value = SimpleNamespace(bucket='private', path='object')
            if failure_stage == 'upload':
                storage.upload.side_effect = StorageUploadError()
            else:
                repo.finalize_image.side_effect = RuntimeError('lost acknowledgement')
            original = SimpleNamespace(settings=settings(), http_client=None)
            composition = SimpleNamespace(title='제목', encouragement_text='위로', image_prompt='숲')
            job = {'id': 'job', 'lease_token': 'current', 'options': {
                'text_model': 'text', 'image_model': 'image', 'image_size': '1024x1024', 'prompt_version': 'diary-v1'}}
            with patch('app.diary.worker.CodysseyClient', return_value=provider), \
                    patch('app.diary.worker.compose_diary', new=AsyncMock(return_value=composition)):
                await DiaryWorker(repo, original, storage).process(job)
            provider.generate_image.assert_awaited_once()
            repo.fail_image.assert_awaited_once_with('job', 'current', code)
            if failure_stage == 'upload':
                repo.finalize_image.assert_not_awaited()
