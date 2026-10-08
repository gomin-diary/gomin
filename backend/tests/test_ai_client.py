import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
import httpx
from pydantic import ValidationError

from app.ai import AIConfigurationError, CodysseyClient
from app.ai.dependencies import get_ai_client
from app.core.config import Settings


def settings(**overrides):
    # No real environment file or inherited provider configuration is used.
    with patch.dict(os.environ, {}, clear=True):
        return Settings(_env_file=None, supabase_url="https://example.supabase.co",
                        supabase_secret_key="test-only", **overrides)


class AISettingsTests(unittest.TestCase):
    def test_environment_key_is_loaded_and_masked(self):
        with patch.dict(os.environ, {"AI_API_KEY": "test-only-virtual-key"}, clear=True):
            config = Settings(_env_file=None, supabase_url="https://example.supabase.co",
                              supabase_secret_key="test-only")
        self.assertEqual(config.ai_api_key.get_secret_value(), "test-only-virtual-key")
        for output in (str(config), repr(config), config.model_dump_json()):
            self.assertNotIn("test-only-virtual-key", output)

    def test_base_paths_do_not_duplicate_v1(self):
        for origin in ("https://copa.codyssey.kr", "https://copa.codyssey.kr/",
                       "https://gateway.example:8443/"):
            with self.subTest(origin=origin):
                config = settings(ai_base_url=origin)
                base = origin.rstrip("/")
                self.assertEqual(config.ai_openai_base_url, base + "/v1")
                self.assertEqual(config.ai_text_url, base + "/v1/chat/completions")
                self.assertEqual(config.ai_image_url, base + "/api/v1/images")

    def test_invalid_origin_is_rejected(self):
        for origin in ("http://gateway.example", "https://gateway.example/v1",
                       "https://gateway.example/api/v1/images",
                       "https://gateway.example/?option=1", "https://gateway.example/#fragment",
                       "https://name:placeholder@gateway.example"):
            with self.subTest(origin=origin):
                with self.assertRaises(ValidationError):
                    settings(ai_base_url=origin)

    def test_default_models_are_separate_and_can_be_overridden(self):
        config = settings()
        self.assertEqual(config.ai_text_model, "gpt-5.4-mini")
        self.assertEqual(config.ai_image_model, "gpt-image-2")
        self.assertEqual(config.ai_image_response_format, "b64_json")
        config = settings(ai_text_model="text-example", ai_image_model="image-example")
        self.assertEqual(config.ai_text_model, "text-example")
        self.assertEqual(config.ai_image_model, "image-example")
        for field, value in (("ai_text_model", ""), ("ai_text_model", "model name"),
                             ("ai_image_model", " "), ("ai_image_model", "model\n")):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    settings(**{field: value})

    def test_timeout_and_response_format_are_validated(self):
        for timeout in (0, -1, 601, float("inf"), float("nan")):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValidationError):
                    settings(ai_timeout_seconds=timeout)
        with self.assertRaises(ValidationError):
            settings(ai_image_response_format="url")


class AIClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_requests_reach_separate_endpoints_with_environment_configuration(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"mock": True})

        config = settings(ai_api_key="test-only-virtual-key", ai_image_model="image-example",
                          ai_base_url="https://gateway.example/", ai_timeout_seconds=45)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = CodysseyClient(http_client, config)
            messages = [{"role": "user", "content": "오늘 힘들었어"}]
            text = client.build_text_request(messages)
            image = client.build_image_request("확정 요약의 그림", size="1024x1024")
            self.assertEqual(requests, [])  # Construction never sends a paid request.
            await http_client.send(text)
            await http_client.send(image)
            self.assertIs(client.http_client, http_client)
            self.assertFalse(http_client.is_closed)
        self.assertEqual([str(r.url) for r in requests], [
            "https://gateway.example/v1/chat/completions",
            "https://gateway.example/api/v1/images",
        ])
        for request in requests:
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.headers["Authorization"], "Bearer test-only-virtual-key")
            self.assertEqual(request.headers["Content-Type"], "application/json")
            self.assertTrue(all(t == 45 for t in request.extensions["timeout"].values()))
        self.assertEqual(json.loads(requests[0].content), {
            "model": "gpt-5.4-mini", "messages": messages,
        })
        self.assertEqual(json.loads(requests[1].content), {
            "model": "image-example", "prompt": "확정 요약의 그림", "size": "1024x1024",
            "response_format": "b64_json",
        })

    async def test_unconfigured_or_invalid_key_never_builds_a_request(self):
        for key in ("", " ", "test key", "test\nkey", "test\rkey", "키", "test\x7fkey"):
            with self.subTest(key_length=len(key)):
                async with httpx.AsyncClient() as http_client:
                    client = CodysseyClient(http_client, settings(ai_api_key=key,
                                                                 ai_image_model="image-example"))
                    with patch.object(http_client, "build_request") as build:
                        for operation in (lambda: client.build_text_request([]),
                                          lambda: client.build_image_request("prompt", size="auto")):
                            with self.assertRaises(AIConfigurationError) as caught:
                                operation()
                            self.assertEqual(str(caught.exception),
                                             "AI_API_KEY must be a non-empty ASCII token")
                        build.assert_not_called()

    async def test_missing_image_model_does_not_fall_back_to_text_model(self):
        async with httpx.AsyncClient() as http_client:
            client = CodysseyClient(http_client, settings(ai_api_key="test-only", ai_image_model=""))
            with patch.object(http_client, "build_request") as build:
                with self.assertRaisesRegex(AIConfigurationError, "AI_IMAGE_MODEL"):
                    client.build_image_request("prompt", size="auto")
                build.assert_not_called()

    async def test_default_image_request_uses_gpt_image_2(self):
        async with httpx.AsyncClient() as http_client:
            client = CodysseyClient(http_client, settings(ai_api_key="test-only"))
            request = client.build_image_request("요약의 그림", size="1024x1024")
        self.assertEqual(json.loads(request.content)["model"], "gpt-image-2")

    async def test_lifespan_owns_the_shared_client_and_dependency(self):
        config = settings()
        with patch("app.core.config.get_settings", return_value=config):
            from app import main
        app = FastAPI()
        with patch.object(main, "settings", config), patch.object(
            main, "create_supabase_client", new=AsyncMock(return_value=object()),
        ) as create_db:
            async with main.lifespan(app):
                client = get_ai_client(SimpleNamespace(app=app))
                shared = create_db.call_args.args[1]
                self.assertIs(client, app.state.ai_client)
                self.assertIs(client.http_client, shared)
                self.assertIs(client.settings, config)
                self.assertFalse(shared.is_closed)
            self.assertTrue(shared.is_closed)


if __name__ == "__main__":
    unittest.main()
