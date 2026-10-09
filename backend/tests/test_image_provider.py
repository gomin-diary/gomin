import asyncio
import base64
import json
import unittest

import httpx

from app.ai import AIConfigurationError, AIRequestError, GeminiClient
from test_ai_client import settings


def image_response(data, *, mime_type="image/png", finish_reason="STOP"):
    return {"candidates": [{"finishReason": finish_reason, "content": {"role": "model", "parts": [
        {"text": "Generated image"}, {"inlineData": {"mimeType": mime_type, "data": data}},
    ]}}]}


class ImageProviderTests(unittest.IsolatedAsyncioTestCase):
    async def generate(self, handler, **overrides):
        config = settings(gemini_api_key="test-only", gemini_image_model="image-example", **overrides)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            return await GeminiClient(http_client, config).generate_image("고민을 담은 그림")

    async def test_base64_endpoint_request_and_bytes(self):
        calls = []
        data = b"image-bytes-for-adapter-test"
        def handle(request):
            calls.append(request)
            self.assertEqual(str(request.url), "https://generativelanguage.googleapis.com/v1beta/models/image-example:generateContent")
            self.assertEqual(request.headers["x-goog-api-key"], "test-only")
            self.assertEqual(json.loads(request.content), {
                "contents": [{"role": "user", "parts": [{"text": "고민을 담은 그림"}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": "1:1"}},
            })
            return httpx.Response(200, json=image_response(base64.b64encode(data).decode()))
        self.assertEqual(await self.generate(handle), data)
        self.assertEqual(len(calls), 1)

    async def test_invalid_responses_are_sanitized(self):
        for body in ({}, [], {"candidates": []}, {"promptFeedback": {"blockReason": "SAFETY"}},
                     {"candidates": [{"finishReason": "STOP", "content": {"role": "model", "parts": [{"text": "refused"}]}}]},
                     {"candidates": [{"finishReason": "STOP", "content": {"role": "model", "parts": [None]}}]},
                     image_response(""), image_response("not base64"), image_response(4), image_response("é"),
                     image_response("YQ==", mime_type="text/html"),
                     image_response("YQ==", finish_reason="SAFETY"),
                     image_response("YQ==", finish_reason="MAX_TOKENS")):
            with self.subTest(body_type=type(body).__name__):
                with self.assertRaises(AIRequestError) as caught:
                    await self.generate(lambda r: httpx.Response(200, json=body))
                self.assertEqual(caught.exception.code, "INVALID_RESPONSE")
                self.assertTrue(caught.exception.uncertain)
                self.assertEqual(str(caught.exception), "AI provider request failed")
                self.assertTrue(caught.exception.__suppress_context__)
        with self.assertRaises(AIRequestError):
            await self.generate(lambda r: httpx.Response(200, text="test-only"))

    async def test_limits_cover_encoded_response_and_decoded_bytes(self):
        for raw in (b"12345", b"" ):
            with self.assertRaises(AIRequestError):
                await self.generate(lambda r: httpx.Response(200, json=image_response(base64.b64encode(raw).decode())),
                                    storage_max_file_size_bytes=4)
        with self.assertRaises(AIRequestError) as caught:
            await self.generate(lambda r: httpx.Response(200, content=b"x" * 70000),
                                storage_max_file_size_bytes=4)
        self.assertEqual(caught.exception.code, "RESPONSE_TOO_LARGE")

    async def test_failures_never_retry_or_follow_redirects(self):
        for status in (302, 400, 401, 403, 408, 409, 429, 500, 503):
            calls = []
            def handle(request):
                calls.append(request)
                return httpx.Response(status, json={"private": "test-only"},
                                      headers={"Location": "https://elsewhere.example"})
            with self.subTest(status=status):
                with self.assertRaises(AIRequestError) as caught:
                    await self.generate(handle)
                self.assertEqual(len(calls), 1)
                self.assertEqual(caught.exception.code, "RATE_LIMITED" if status == 429 else "PROVIDER_ERROR")
                self.assertNotIn("test-only", str(caught.exception))

    async def test_connection_and_read_timeout_are_distinguished(self):
        for error, code, uncertain in ((httpx.ConnectError, "CONNECTION_FAILED", False),
                                       (httpx.ReadTimeout, "TIMEOUT", True)):
            def handle(request):
                raise error("test-only", request=request)
            with self.assertRaises(AIRequestError) as caught:
                await self.generate(handle)
            self.assertEqual(caught.exception.code, code)
            self.assertEqual(caught.exception.uncertain, uncertain)
            self.assertTrue(caught.exception.__suppress_context__)

    async def test_missing_configuration_never_sends(self):
        config = settings()
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: self.fail("must not send"))) as http_client:
            with self.assertRaises(AIConfigurationError):
                await GeminiClient(http_client, config).generate_image("prompt")

    async def test_stream_is_closed_when_total_timeout_expires(self):
        class SlowStream(httpx.AsyncByteStream):
            closed = False
            async def __aiter__(self):
                await asyncio.sleep(1)
                yield b"{}"
            async def aclose(self):
                self.closed = True
        stream = SlowStream()
        with self.assertRaises(AIRequestError) as caught:
            await self.generate(lambda r: httpx.Response(200, stream=stream), gemini_timeout_seconds=0.01)
        self.assertEqual(caught.exception.code, "TIMEOUT")
        self.assertTrue(stream.closed)

    async def test_thought_image_is_skipped_and_final_image_is_used(self):
        body = image_response("ZmluYWw=")
        body["candidates"][0]["content"]["parts"].insert(0, {
            "thought": True, "inlineData": {"mimeType": "image/png", "data": "dGhvdWdodA=="},
        })
        self.assertEqual(await self.generate(lambda r: httpx.Response(200, json=body)), b"final")
