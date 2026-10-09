import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
import httpx
from pydantic import ValidationError

from app.ai import AIConfigurationError, CodysseyClient, GeminiClient
from app.ai.dependencies import get_ai_client, get_image_ai_client
from app.core.config import Settings


def settings(**overrides):
    # No real environment file or inherited provider configuration is used.
    with patch.dict(os.environ, {}, clear=True):
        return Settings(_env_file=None, supabase_url="https://example.supabase.co",
                        supabase_secret_key="test-only", **overrides)


class AISettingsTests(unittest.TestCase):
    def test_environment_key_is_loaded_and_masked(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-google-key", "AI_API_KEY": "test-only-copa-key"}, clear=True):
            config = Settings(_env_file=None, supabase_url="https://example.supabase.co",
                              supabase_secret_key="test-only")
        self.assertEqual(config.gemini_api_key.get_secret_value(), "test-only-google-key")
        self.assertEqual(config.ai_api_key.get_secret_value(), "test-only-copa-key")
        for output in (str(config), repr(config), config.model_dump_json()):
            self.assertNotIn("test-only-google-key", output)
            self.assertNotIn("test-only-copa-key", output)

    def test_model_endpoints_use_the_configured_origin(self):
        for origin in ("https://generativelanguage.googleapis.com", "https://generativelanguage.googleapis.com/",
                       "https://gateway.example:8443/"):
            with self.subTest(origin=origin):
                config = settings(ai_base_url=origin, gemini_base_url=origin)
                base = origin.rstrip("/")
                self.assertEqual(config.ai_text_url, base + "/v1/chat/completions")
                self.assertEqual(config.gemini_image_url, base + "/v1beta/models/gemini-2.5-flash-image:generateContent")

    def test_invalid_origin_is_rejected(self):
        for origin in ("http://gateway.example", "https://gateway.example/v1",
                       "https://gateway.example/api/v1/images",
                       "https://gateway.example/?option=1", "https://gateway.example/#fragment",
                       "https://name:placeholder@gateway.example"):
            with self.subTest(origin=origin):
                with self.assertRaises(ValidationError):
                    settings(gemini_base_url=origin)
                with self.assertRaises(ValidationError):
                    settings(ai_base_url=origin)

    def test_copa_environment_is_preserved_and_does_not_override_gemini(self):
        with patch.dict(os.environ, {"AI_BASE_URL": "https://copa.codyssey.kr", "AI_API_KEY": "old-test-key",
                                     "AI_TEXT_MODEL": "gpt-5.4-mini", "AI_IMAGE_MODEL": "gpt-image-2"}, clear=True):
            config = Settings(_env_file=None, supabase_url="https://example.supabase.co",
                              supabase_secret_key="test-only")
        self.assertEqual(str(config.gemini_base_url), "https://generativelanguage.googleapis.com/")
        self.assertEqual(config.gemini_api_key.get_secret_value(), "")
        self.assertEqual(config.ai_text_model, "gpt-5.4-mini")
        self.assertEqual(config.ai_api_key.get_secret_value(), "old-test-key")
        self.assertEqual(str(config.ai_base_url), "https://copa.codyssey.kr/")
        self.assertEqual(config.gemini_image_model, "gemini-2.5-flash-image")

    def test_default_models_are_separate_and_can_be_overridden(self):
        config = settings()
        self.assertEqual(config.ai_text_model, "gpt-5.4-mini")
        self.assertEqual(config.gemini_image_model, "gemini-2.5-flash-image")
        config = settings(ai_text_model="text-example", gemini_image_model="image-example")
        self.assertEqual(config.ai_text_model, "text-example")
        self.assertEqual(config.gemini_image_model, "image-example")
        for field, value in (("ai_text_model", ""), ("ai_text_model", "model name"),
                             ("gemini_image_model", " "), ("gemini_image_model", "model\n"),
                             ("gemini_image_model", "models/image"), ("gemini_image_model", "image:generateContent")):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    settings(**{field: value})

    def test_timeout_and_aspect_ratio_are_validated(self):
        for timeout in (0, -1, 601, float("inf"), float("nan")):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValidationError):
                    settings(gemini_timeout_seconds=timeout)
                with self.assertRaises(ValidationError):
                    settings(ai_timeout_seconds=timeout)
        with self.assertRaises(ValidationError):
            settings(gemini_image_aspect_ratio="1024x1024")


class AIClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_requests_reach_separate_endpoints_with_environment_configuration(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"mock": True})

        config = settings(ai_api_key="test-only-copa-key", ai_base_url="https://copa-gateway.example/", ai_timeout_seconds=30,
                          gemini_api_key="test-only-google-key", gemini_image_model="image-example",
                          gemini_base_url="https://gateway.example/", gemini_timeout_seconds=45,
                          gemini_image_aspect_ratio="16:9")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = CodysseyClient(http_client, config)
            image_client = GeminiClient(http_client, config)
            messages = [{"role": "user", "content": "오늘 힘들었어"}]
            text = client.build_text_request(messages)
            image = image_client.build_image_request("확정 요약의 그림")
            self.assertEqual(requests, [])  # Construction never sends a paid request.
            await http_client.send(text)
            await http_client.send(image)
            self.assertIs(client.http_client, http_client)
            self.assertFalse(http_client.is_closed)
        self.assertEqual([str(r.url) for r in requests], [
            "https://copa-gateway.example/v1/chat/completions",
            "https://gateway.example/v1beta/models/image-example:generateContent",
        ])
        for request in requests:
            self.assertEqual(request.method, "POST")
            self.assertNotIn("test-only-google-key", str(request.url))
            self.assertEqual(request.headers["Content-Type"], "application/json")
        self.assertEqual(requests[0].headers["Authorization"], "Bearer test-only-copa-key")
        self.assertNotIn("x-goog-api-key", requests[0].headers)
        self.assertEqual(requests[1].headers["x-goog-api-key"], "test-only-google-key")
        self.assertNotIn("Authorization", requests[1].headers)
        self.assertTrue(all(t == 30 for t in requests[0].extensions["timeout"].values()))
        self.assertTrue(all(t == 45 for t in requests[1].extensions["timeout"].values()))
        self.assertEqual(json.loads(requests[0].content), {
            "model": "gpt-5.4-mini", "messages": messages,
        })
        self.assertEqual(json.loads(requests[1].content), {
            "contents": [{"role": "user", "parts": [{"text": "확정 요약의 그림"}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": "16:9"}},
        })

    async def test_unconfigured_or_invalid_key_never_builds_a_request(self):
        for key in ("", " ", "test key", "test\nkey", "test\rkey", "키", "test\x7fkey"):
            with self.subTest(key_length=len(key)):
                async with httpx.AsyncClient() as http_client:
                    config = settings(ai_api_key=key, gemini_api_key=key, gemini_image_model="image-example")
                    client = CodysseyClient(http_client, config)
                    image_client = GeminiClient(http_client, config)
                    with patch.object(http_client, "build_request") as build:
                        for operation, field in ((lambda: client.build_text_request([]), "AI_API_KEY"),
                                                  (lambda: image_client.build_image_request("prompt"), "GEMINI_API_KEY")):
                            with self.assertRaises(AIConfigurationError) as caught:
                                operation()
                            self.assertEqual(str(caught.exception),
                                             f"{field} must be a non-empty ASCII token")
                        build.assert_not_called()

    async def test_missing_image_model_does_not_fall_back_to_text_model(self):
        async with httpx.AsyncClient() as http_client:
            client = GeminiClient(http_client, settings(gemini_api_key="test-only", gemini_image_model=""))
            with patch.object(http_client, "build_request") as build:
                with self.assertRaisesRegex(AIConfigurationError, "GEMINI_IMAGE_MODEL"):
                    client.build_image_request("prompt")
                build.assert_not_called()

    async def test_default_image_request_uses_gemini_flash_image(self):
        async with httpx.AsyncClient() as http_client:
            client = GeminiClient(http_client, settings(gemini_api_key="test-only"))
            request = client.build_image_request("요약의 그림")
        self.assertEqual(request.url.path, "/v1beta/models/gemini-2.5-flash-image:generateContent")

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
                self.assertIsInstance(client, CodysseyClient)
                image_client = get_image_ai_client(SimpleNamespace(app=app))
                self.assertIsInstance(image_client, GeminiClient)
                self.assertIs(image_client.http_client, shared)
                self.assertIs(image_client.settings, config)
                self.assertFalse(shared.is_closed)
            self.assertTrue(shared.is_closed)


if __name__ == "__main__":
    unittest.main()
