import asyncio
import base64
import json
import unittest

import httpx

from app.ai import AIConfigurationError, AIRequestError, CodysseyClient
from test_ai_client import settings


class ImageProviderTests(unittest.IsolatedAsyncioTestCase):
    async def generate(self, handler, **overrides):
        config = settings(ai_api_key="test-only", ai_image_model="image-example", **overrides)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            return await CodysseyClient(http_client, config).generate_image("고민을 담은 그림", size="1024x1024")

    async def test_base64_endpoint_request_and_bytes(self):
        calls = []
        data = b"image-bytes-for-adapter-test"
        def handle(request):
            calls.append(request)
            self.assertEqual(str(request.url), "https://copa.codyssey.kr/api/v1/images")
            self.assertEqual(request.headers["Authorization"], "Bearer test-only")
            self.assertEqual(json.loads(request.content), {
                "model": "image-example", "prompt": "고민을 담은 그림", "size": "1024x1024",
                "response_format": "b64_json",
            })
            return httpx.Response(200, json={"result": {"images": [
                {"b64_json": base64.b64encode(data).decode(), "url": "https://session-only.example"},
            ]}})
        self.assertEqual(await self.generate(handle), data)
        self.assertEqual(len(calls), 1)

    async def test_invalid_responses_are_sanitized(self):
        for body in ({}, [], {"result": {"images": []}},
                     {"result": {"images": [{"url": "https://session-only.example"}]}},
                     {"result": {"images": [{"b64_json": ""}]}},
                     {"result": {"images": [{"b64_json": "not base64"}]}},
                     {"result": {"images": [{"b64_json": 4}]}},
                     {"result": {"images": [{"b64_json": "é"}]}}):
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
                await self.generate(lambda r: httpx.Response(200, json={"result": {"images": [
                    {"b64_json": base64.b64encode(raw).decode()},
                ]}}), storage_max_file_size_bytes=4)
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
                await CodysseyClient(http_client, config).generate_image("prompt", size="auto")

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
            await self.generate(lambda r: httpx.Response(200, stream=stream), ai_timeout_seconds=0.01)
        self.assertEqual(caught.exception.code, "TIMEOUT")
        self.assertTrue(stream.closed)
