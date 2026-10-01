import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import ConnectError
from pydantic import BaseModel

from app.config import Settings

# Never load a real environment file or connect to an external service.
settings = Settings(
    _env_file=None,
    supabase_url="https://example.supabase.co",
    supabase_secret_key="test-only-placeholder",
)
with patch("app.config.get_settings", return_value=settings):
    from app.main import app
from app.database import get_supabase


class Input(BaseModel):
    count: int


class MappingInput(BaseModel):
    values: dict[int, int]


class NestedInput(BaseModel):
    items: list[Input]


@app.post("/_test/nested")
async def nested(payload: NestedInput):
    return payload


@app.post("/_test/mapping")
async def mapping(payload: MappingInput):
    return payload


@app.post("/_test/validation")
async def validation(payload: Input):
    return payload


@app.get("/_test/internal")
async def internal():
    raise RuntimeError("private-value")


@app.get("/_test/headers")
async def headers():
    raise HTTPException(401, detail="private-value", headers={"WWW-Authenticate": "Bearer"})


class Database:
    def __init__(self, result=True, failure=False):
        self.result = result
        self.failure = failure

    def rpc(self, name):
        if name != "health_check":
            raise AssertionError("Unexpected RPC")
        return self

    async def execute(self):
        if self.failure:
            raise ConnectError("private-value")
        return SimpleNamespace(data=self.result)


class ResponseTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        app.dependency_overrides[get_supabase] = lambda: Database()

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def test_health_uses_success_envelope(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True, "data": {"status": "ok"}, "error": None})

    def test_database_success(self):
        response = self.client.get("/api/v1/health/db")
        self.assertEqual(response.json(), {"success": True, "data": {"status": "ok", "database": "connected"}, "error": None})

    def test_database_failure_preserves_503(self):
        for database in (Database(result=False), Database(failure=True)):
            with self.subTest(database=database):
                app.dependency_overrides[get_supabase] = lambda: database
                response = self.client.get("/api/v1/health/db")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["error"]["code"], "SERVICE_UNAVAILABLE")
                self.assertIsNone(response.json()["data"])
                self.assertNotIn("private-value", response.text)

    def test_validation_sanitizes_input(self):
        response = self.client.post("/_test/validation", json={"count": "private-value"})
        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"][0]["path"], ["body", "count"])
        self.assertEqual(body["error"]["details"][0]["code"], "INVALID_FORMAT")
        self.assertNotIn("private-value", response.text)

    def test_validation_does_not_echo_dynamic_mapping_keys(self):
        response = self.client.post("/_test/mapping", json={"values": {"private-value": 1}})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["details"][0]["path"], ["body", "values", "[redacted]", "[key]"])
        self.assertNotIn("private-value", response.text)

    def test_nested_validation_preserves_declared_fields_and_indices(self):
        response = self.client.post("/_test/nested", json={"items": [{"count": "private-value"}]})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["details"][0]["path"], ["body", "items", 0, "count"])
        self.assertNotIn("private-value", response.text)

    def test_http_error_preserves_headers_and_hides_detail(self):
        response = self.client.get("/_test/headers")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")
        self.assertNotIn("private-value", response.text)

    def test_missing_route_uses_failure_envelope(self):
        response = self.client.get("/api/v1/missing")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")

    def test_unhandled_error_is_safe_500(self):
        response = self.client.get("/_test/internal")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("private-value", response.text)

    def test_internal_error_remains_readable_from_frontend_origin(self):
        response = self.client.get("/_test/internal", headers={"Origin": "http://localhost:3000"})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:3000")

    def test_openapi_documents_success_and_error_models(self):
        operation = self.client.get("/openapi.json").json()["paths"]["/api/v1/health/db"]["get"]
        for status in ("200", "422", "500", "503"):
            self.assertIn("schema", operation["responses"][status]["content"]["application/json"])


if __name__ == "__main__":
    unittest.main()
