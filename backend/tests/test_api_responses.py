import unittest
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import patch

from fastapi import Cookie, Depends, Header, HTTPException, Path as PathParam, Query
from fastapi.testclient import TestClient
from httpx import ConnectError
from pydantic import AliasChoices, AliasPath, BaseModel, ConfigDict, Field

from app.core.config import Settings

# Never load a real environment file or connect to an external service.
settings = Settings(
    _env_file=None,
    supabase_url="https://example.supabase.co",
    supabase_secret_key="test-only-placeholder",
)
with patch("app.core.config.get_settings", return_value=settings):
    from app.main import app
from app.db.client import get_supabase


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


class AliasInput(BaseModel):
    count: int = Field(validation_alias=AliasChoices("count", "quantity"))
    items: list[Input] = Field(validation_alias=AliasPath("payload", "items"))
    values: dict[str, Input] = Field(validation_alias=AliasChoices("values", AliasPath("payload", "values")))


@app.post("/_test/aliases")
async def aliases(payload: AliasInput):
    return payload


def dependency_inputs(
    item_id: int = PathParam(),
    limit: int = Query(10),
    token: int = Header(1, alias="X-Token"),
    session: int = Cookie(1),
):
    return item_id


def nested_dependency(value: int = Depends(dependency_inputs)):
    return value


@app.get("/_test/dependencies/{item_id}")
async def dependencies(value: int = Depends(nested_dependency)):
    return value


class NamedInput(BaseModel):
    model_config = ConfigDict(validate_by_name=True)
    count: int = Field(alias="quantity")


class NameLocationInput(BaseModel):
    model_config = ConfigDict(loc_by_alias=False)
    count: int = Field(alias="quantity")


class OtherInput(BaseModel):
    name: int


class UnionInput(BaseModel):
    items: list[Input | OtherInput]
    values: dict[str, Input | OtherInput]


class Filters(BaseModel):
    limit: int = 10
    model_config = ConfigDict(extra="forbid")


@app.post("/_test/named-input")
async def named_input(payload: NamedInput):
    return payload


@app.post("/_test/name-location")
async def name_location(payload: NameLocationInput):
    return payload


@app.post("/_test/union")
async def union_input(payload: Input | OtherInput):
    return payload


@app.post("/_test/nested-union")
async def nested_union_input(payload: UnionInput):
    return payload


@app.get("/_test/query-model")
async def query_model(filters: Annotated[Filters, Query()]):
    return filters


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

    def test_nested_dependency_preserves_input_paths(self):
        response = self.client.get(
            "/_test/dependencies/private-value?limit=private-value",
            headers={"X-Token": "private-value", "Cookie": "session=private-value"},
        )
        self.assertEqual(response.status_code, 422)
        paths = [detail["path"] for detail in response.json()["error"]["details"]]
        self.assertCountEqual(paths, [["path", "item_id"], ["query", "limit"], ["header", "X-Token"], ["cookie", "session"]])
        self.assertNotIn("private-value", response.text)

    def test_alias_choices_preserve_submitted_field_name(self):
        for alias in ("count", "quantity"):
            with self.subTest(alias=alias):
                response = self.client.post("/_test/aliases", json={alias: "private-value", "payload": {"items": [], "values": {}}})
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["error"]["details"][0]["path"], ["body", alias])
                self.assertNotIn("private-value", response.text)

    def test_alias_path_preserves_nested_fields_and_indices(self):
        response = self.client.post("/_test/aliases", json={"count": 1, "payload": {"items": [{"count": "private-value"}], "values": {}}})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["details"][0]["path"], ["body", "payload", "items", 0, "count"])
        self.assertNotIn("private-value", response.text)

    def test_alias_choices_with_path_still_hide_mapping_keys(self):
        for payload in ({"values": {"private-key": {"count": "private-value"}}, "payload": {"items": []}},
                        {"payload": {"items": [], "values": {"private-key": {"count": "private-value"}}}}):
            with self.subTest(payload=payload):
                response = self.client.post("/_test/aliases", json={"count": 1, **payload})
                self.assertEqual(response.status_code, 422)
                prefix = ["body", "values"] if "values" in payload else ["body", "payload", "values"]
                self.assertEqual(response.json()["error"]["details"][0]["path"], [*prefix, "[redacted]", "count"])
                self.assertNotIn("private-key", response.text)
                self.assertNotIn("private-value", response.text)

    def test_alias_model_preserves_allowed_original_name(self):
        for field in ("count", "quantity"):
            with self.subTest(field=field):
                response = self.client.post("/_test/named-input", json={field: "private-value"})
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["error"]["details"][0]["path"], ["body", field])
                self.assertNotIn("private-value", response.text)

    def test_model_can_report_field_names_instead_of_aliases(self):
        response = self.client.post("/_test/name-location", json={"quantity": "private-value"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["details"][0]["path"], ["body", "count"])
        self.assertNotIn("private-value", response.text)

    def test_union_omits_model_labels_and_preserves_fields(self):
        response = self.client.post("/_test/union", json={"count": "private-value", "name": "private-value"})
        self.assertEqual(response.status_code, 422)
        self.assertCountEqual([detail["path"] for detail in response.json()["error"]["details"]],
                              [["body", "count"], ["body", "name"]])
        self.assertNotIn("private-value", response.text)

    def test_nested_union_preserves_indices_and_hides_mapping_keys(self):
        response = self.client.post("/_test/nested-union", json={
            "items": [{"count": "private-value", "name": "private-value"}],
            "values": {"Input": {"count": "private-value", "name": "private-value"}},
        })
        self.assertEqual(response.status_code, 422)
        self.assertCountEqual([detail["path"] for detail in response.json()["error"]["details"]], [
            ["body", "items", 0, "count"], ["body", "items", 0, "name"],
            ["body", "values", "[redacted]", "count"], ["body", "values", "[redacted]", "name"],
        ])
        self.assertNotIn("private-value", response.text)
        self.assertNotIn("Input", response.text)

    def test_query_model_preserves_fields_and_hides_unknown_keys(self):
        response = self.client.get("/_test/query-model?limit=private-value&private-key=1")
        self.assertEqual(response.status_code, 422)
        self.assertCountEqual([detail["path"] for detail in response.json()["error"]["details"]],
                              [["query", "limit"], ["query", "[redacted]"]])
        self.assertNotIn("private-value", response.text)
        self.assertNotIn("private-key", response.text)

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
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_auth_preflight_allows_credentials_only_from_configured_origins(self):
        for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
            with self.subTest(origin=origin):
                response = self.client.options("/api/v1/auth/login", headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
                self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        response = self.client.options("/api/v1/auth/login", headers={
            "Origin": "https://untrusted.example.test",
            "Access-Control-Request-Method": "POST",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.headers.get("access-control-allow-origin"))

    def test_openapi_documents_success_and_error_models(self):
        operation = self.client.get("/openapi.json").json()["paths"]["/api/v1/health/db"]["get"]
        for status in ("200", "422", "500", "503"):
            self.assertIn("schema", operation["responses"][status]["content"]["application/json"])


if __name__ == "__main__":
    unittest.main()
