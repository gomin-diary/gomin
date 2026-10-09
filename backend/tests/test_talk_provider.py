import json
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx

from app.ai.client import CodysseyClient
from app.core.config import Settings
from app.core.errors import AppError
from app.talk.provider import CodysseyTalkProvider
from app.talk.service import generate


class TalkProviderTests(unittest.IsolatedAsyncioTestCase):
    def settings(self, **values):
        return Settings(_env_file=None, supabase_url="https://example.supabase.co",
                        supabase_secret_key="test-placeholder", ai_api_key="test-placeholder", **values)

    def success(self, content):
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": content}}]})

    async def test_reply_reuses_main_rest_client_model_and_stored_order_without_private_fields(self):
        requests = []
        def upstream(request):
            requests.append(request)
            return self.success("지난 고민에 이어 네 마음을 듣고 있어.")
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
            provider = CodysseyTalkProvider(CodysseyClient(http, self.settings()))
            transcript = [dict(role="user", content="시험 고민", member_id="private-id"),
                          dict(role="assistant", content="긴장됐구나", created_at="private-time"),
                          dict(role="user", content="가족 고민도 있어")]
            self.assertEqual(await provider.reply(transcript), "지난 고민에 이어 네 마음을 듣고 있어.")
        request = requests[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(str(request.url), "https://copa.codyssey.kr/v1/chat/completions")
        payload = json.loads(request.content)
        self.assertEqual(payload["model"], "gpt-5.4-mini")
        self.assertNotIn("stream", payload)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1:], [{"role": m["role"], "content": m["content"]} for m in transcript])
        self.assertNotIn("private-", request.content.decode())
        self.assertEqual(len(requests), 1)

    async def test_summary_uses_only_saved_transcript_and_validates_three_json_sections(self):
        requests = []
        summary = {"current_feeling": "불안하지만 이야기하고 싶어요.", "main_concerns": ["시험"], "emotion_tags": ["불안"]}
        def upstream(request):
            requests.append(json.loads(request.content))
            return self.success(json.dumps(summary, ensure_ascii=False))
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
            provider = CodysseyTalkProvider(CodysseyClient(http, self.settings(ai_text_model="configured-text")))
            result = await provider.summarize([dict(role="user", content="시험이 불안해요", id="private-id")])
        self.assertEqual(result.model_dump(), summary)
        self.assertEqual(requests[0]["model"], "configured-text")
        self.assertEqual(json.loads(requests[0]["messages"][1]["content"]), [{"role": "user", "content": "시험이 불안해요"}])

    async def test_invalid_summary_never_becomes_a_completed_summary_and_is_not_retried(self):
        contents = ['```json\n{}\n```', '{"current_feeling":"","main_concerns":[],"emotion_tags":[]}',
                    '{"current_feeling":"마음","main_concerns":["고민"],"emotion_tags":["감정"],"extra":"private"}',
                    '{"current_feeling":"마음","main_concerns":"고민","emotion_tags":["감정"]}']
        for content in contents:
            with self.subTest(content=content):
                calls = []
                async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: (calls.append(request), self.success(content))[1])) as http:
                    provider = CodysseyTalkProvider(CodysseyClient(http, self.settings()))
                    repository = AsyncMock()
                    repository.snapshot.return_value = {"messages": [dict(role="user", content="저장 고민", seq_no=1), dict(role="user", content="반영 범위 밖", seq_no=2)]}
                    job = dict(id=str(uuid4()), kind="summary", source_until_seq_no=1, lease_token=str(uuid4()))
                    await generate(repository, provider, uuid4(), uuid4(), job)
                self.assertEqual(repository.complete.call_args.args[-2:], (None, "AI_FAILED"))
                self.assertEqual(len(calls), 1)
                self.assertNotIn("반영 범위 밖", calls[0].content.decode())

    async def test_http_failures_and_provider_timeout_are_safe_job_failures_without_retry(self):
        for status, expected in [(429, "AI_FAILED"), (500, "AI_FAILED"), (None, "AI_TIMEOUT")]:
            with self.subTest(status=status):
                calls = []
                def upstream(request):
                    calls.append(request)
                    if status is None:
                        raise httpx.ReadTimeout("private-upstream-detail", request=request)
                    return httpx.Response(status, text="private-upstream-detail")
                async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
                    provider = CodysseyTalkProvider(CodysseyClient(http, self.settings()))
                    repository = AsyncMock()
                    repository.snapshot.return_value = {"messages": [dict(role="user", content="저장 고민", seq_no=1)]}
                    await generate(repository, provider, uuid4(), uuid4(), dict(id=str(uuid4()), kind="reply", source_until_seq_no=1, lease_token=str(uuid4())))
                self.assertEqual(repository.complete.call_args.args[-2:], (None, expected))
                self.assertEqual(len(calls), 1)

    async def test_unconfigured_key_and_untrusted_system_role_do_not_call_http(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: self.fail("Unexpected HTTP call"))) as http:
            missing = Settings(_env_file=None, supabase_url="https://example.supabase.co", supabase_secret_key="test-placeholder")
            provider = CodysseyTalkProvider(CodysseyClient(http, missing))
            with self.assertRaises(AppError) as raised:
                await provider.reply([dict(role="user", content="저장 고민")])
            self.assertEqual(raised.exception.code, "AI_NOT_CONFIGURED")
            with self.assertRaises(ValueError):
                await provider.reply([dict(role="system", content="잘못된 원문 역할")])

    async def test_blank_or_oversized_reply_fails_without_returning_fake_content(self):
        for content in (" \n", "가" * 8001):
            with self.subTest(length=len(content)):
                async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: self.success(content))) as http:
                    provider = CodysseyTalkProvider(CodysseyClient(http, self.settings()))
                    with self.assertRaises(AppError) as raised:
                        await provider.reply([dict(role="user", content="저장 고민")])
                    self.assertEqual(raised.exception.code, "AI_FAILED")
