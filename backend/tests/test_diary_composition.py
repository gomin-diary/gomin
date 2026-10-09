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
            for requirement in ("자연 경관", "뒷모습", "정면 모습", "전신샷은 필수가 아닙니다", "사진처럼 실사", "실제 동물로 실사화하지",
                                "시각적 비유", "포근하고 서정적인", "억지로 밝은 미소", "접촉 그림자", "전신·정면 포즈를 강제하지",
                                "메시지·제목·문자·워터마크를 넣지", "50~80자", "한국어 두 문장", "줄바꿈 한 개", "JSON 문자열에서는",
                                "첫 문장은 요약의 감정을", "두 번째 문장은 부담을 덜어", "모리의 이야기는 덧붙이지"):
                self.assertIn(requirement, body["messages"][0]["content"])
            self.assertNotIn("35자 이내", body["messages"][0]["content"])
            self.assertNotIn("줄바꿈 없이", body["messages"][0]["content"])
            self.assertNotIn("40~50%", body["messages"][0]["content"])
            self.assertNotIn("중앙 60%", body["messages"][0]["content"])
            self.assertNotIn("이미지 위에도 얹을", body["messages"][0]["content"])
            self.assertNotIn("오른쪽 상단", body["messages"][0]["content"])
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

    async def test_two_sentence_encouragement_preserves_json_escaped_line_break(self):
        encouragement = "처음이라 마음이 흔들리는 건 자연스러운 일이에요.\n서두르지 않아도 괜찮으니, 당신의 속도로 천천히 걸어가요."
        output = {"title": "처음의 마음", "encouragement_text": encouragement, "image_prompt": "모리가 숲을 바라보는 장면"}
        result = await self.compose(json.dumps(output))
        self.assertEqual(result.encouragement_text, encouragement)
        self.assertEqual(len(result.encouragement_text.splitlines()), 2)
