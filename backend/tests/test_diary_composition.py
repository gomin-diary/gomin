import json
import unittest

import httpx

from app.ai.client import AIRequestError, CodysseyClient
from app.diary.composition import compose_diary
from test_ai_client import settings


class DiaryCompositionTests(unittest.IsolatedAsyncioTestCase):
    async def compose(self, output, finish_reason="stop"):
        def handler(request):
            body = json.loads(request.content)
            self.assertEqual(body["model"], "gpt-5.4-mini")
            self.assertEqual(str(request.url), "https://copa.codyssey.kr/v1/chat/completions")
            self.assertIn("모리(Mori)", body["messages"][0]["content"])
            submitted = json.loads(body["messages"][1]["content"])
            self.assertEqual(submitted, {"current_feeling": "불안해요", "main_concerns": ["시험"], "emotion_tags": ["불안"]})
            return httpx.Response(200, json={"choices": [{"finish_reason": finish_reason,
                "message": {"role": "assistant", "content": output}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            return await compose_diary(CodysseyClient(http_client, settings(ai_api_key="test-only")), {
                "current_feeling": "불안해요", "main_concerns": ["시험"], "emotion_tags": ["불안"],
                "member_id": "must-not-be-sent", "email": "private@example.test"})

    async def test_model_and_summary_only_data_are_used_and_valid_output_is_returned(self):
        output = {"title": "시험 앞의 마음", "encouragement_text": "한 걸음씩 준비해도 괜찮아요",
                  "image_prompt": "시험을 앞둔 모리가 푸른 숲에서 쉬는 따뜻한 그림일기"}
        result = await self.compose(json.dumps(output))
        self.assertEqual(result.model_dump(), output)

    async def test_blank_malformed_extra_or_truncated_output_never_becomes_a_diary(self):
        for output in ['not-json', '{}', '{"title":" ","encouragement_text":"괜찮아","image_prompt":"숲"}',
                       '{"title":"제목","encouragement_text":"괜찮아","image_prompt":"숲","extra":"x"}']:
            with self.assertRaises(AIRequestError) as error:
                await self.compose(output)
            self.assertEqual(error.exception.code, "INVALID_RESPONSE")
        with self.assertRaises(AIRequestError):
            await self.compose('{"title":"제목"}', finish_reason="length")
