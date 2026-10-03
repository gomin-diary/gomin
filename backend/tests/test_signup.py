import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.sessions import router as sessions_router
from app.auth.session import get_auth_repository, get_auth_settings as auth_settings
from app.api.routes.signup import router, get_settings as signup_settings
from app.auth.crypto import code_digest
from app.auth.security import hash_password, verify_password, token_digest
from app.core.config import Settings, get_settings
from app.core.exception_handlers import ERROR_RESPONSES, register_exception_handlers
from app.db.client import get_supabase
from app.mail import get_mailer
from app.mail.errors import MailConfigurationError, MailDeliveryError

SETTINGS = Settings(_env_file=None, supabase_url="https://example.supabase.co",
                    supabase_secret_key="test-only-placeholder", auth_hmac_key="test-key-" * 8,
                    auth_cookie_secure=False)


class RpcDatabase:
    def __init__(self):
        self.calls = []
        self.results = {}

    def rpc(self, name, params):
        self.calls.append((name, params))
        result = self.results.get(name, {})
        if isinstance(result, Exception):
            return SimpleNamespace(execute=AsyncMock(side_effect=result))
        return SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(data=result)))


class SignupApiTests(unittest.TestCase):
    def setUp(self):
        self.db = RpcDatabase()
        self.mailer = SimpleNamespace(send_verification_email=AsyncMock())
        app = FastAPI(responses=ERROR_RESPONSES)
        register_exception_handlers(app)
        app.include_router(router)
        app.include_router(sessions_router)
        app.dependency_overrides[get_supabase] = lambda: self.db
        app.dependency_overrides[get_mailer] = lambda: self.mailer
        app.dependency_overrides[signup_settings] = lambda: SETTINGS
        app.dependency_overrides[auth_settings] = lambda: SETTINGS
        self.app = app
        self.client = TestClient(app, raise_server_exceptions=False)
        self.member = {"id": str(uuid4()), "email": "member@example.com", "name": "사용자"}
        self.request_id = str(uuid4())
        self.expires = (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat()
        self.db.results["gomin_auth_finish_delivery"] = {"expires_at": self.expires}
        self.db.results["gomin_auth_verify_code"] = {"expires_at": self.expires}
        self.db.results["gomin_auth_signup"] = self.member
        self.payload = {
            "email": " MEMBER@example.com ", "name": " 사용자 ", "password": "  secret password  ",
            "confirmation": "  secret password  ", "verification_proof": "a" * 43,
            "consents": [{"type": kind, "version": "dev-2026-10-02", "agreed": True}
                         for kind in ("terms_of_service", "privacy_collection")],
        }

    def request_code(self):
        return self.client.post("/api/v1/auth/email-verifications", json={"email": " MEMBER@example.com "})

    def test_delivery_accepted_stores_only_hmac_and_sets_expiry_after_send(self):
        response = self.request_code()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["expires_at"], self.expires.replace("+00:00", "Z"))
        call = self.mailer.send_verification_email.call_args
        self.assertEqual(call.args[0], "member@example.com")
        self.assertRegex(call.kwargs["code"], r"^[0-9]{6}$")
        self.assertEqual(call.kwargs["expires_minutes"], 3)
        name, params = self.db.calls[0]
        self.assertEqual(name, "gomin_auth_begin_verification")
        self.assertNotIn(call.kwargs["code"], str(params))
        self.assertEqual(call.kwargs["idempotency_key"], f"signup-verification/{params['p_id']}")
        self.assertEqual(self.db.calls[1][0], "gomin_auth_finish_delivery")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_existing_email_does_not_send(self):
        self.db.results["gomin_auth_begin_verification"] = {"error": "EMAIL_EXISTS"}
        response = self.request_code()
        self.assertEqual(response.status_code, 409)
        self.mailer.send_verification_email.assert_not_awaited()

    def test_confirmed_failure_marks_failed_but_uncertain_remains_pending(self):
        for error, code, finished in [
            (MailDeliveryError(delivery_uncertain=False), "MAIL_DELIVERY_FAILED", True),
            (MailDeliveryError(delivery_uncertain=True), "MAIL_DELIVERY_UNCERTAIN", False),
            (MailConfigurationError(), "MAIL_NOT_CONFIGURED", True),
        ]:
            with self.subTest(code=code):
                self.db.calls.clear()
                self.mailer.send_verification_email.side_effect = error
                response = self.request_code()
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["error"]["code"], code)
                self.assertEqual(len(self.db.calls), 2 if finished else 1)
                if finished: self.assertFalse(self.db.calls[-1][1]["p_sent"])

    def test_missing_hmac_key_prevents_database_and_delivery(self):
        self.app.dependency_overrides[signup_settings] = lambda: SETTINGS.model_copy(update={"auth_hmac_key": SETTINGS.supabase_secret_key})
        response = self.request_code()
        self.assertEqual(response.json()["error"]["code"], "AUTH_NOT_CONFIGURED")
        self.assertEqual(self.db.calls, [])
        self.mailer.send_verification_email.assert_not_awaited()

    def test_confirmation_returns_proof_but_persists_only_digest(self):
        response = self.client.post("/api/v1/auth/email-verifications/confirm", json={
            "email": "member@example.com", "verification_id": self.request_id, "code": "123456"})
        self.assertEqual(response.status_code, 200)
        proof = response.json()["data"]["verification_proof"]
        self.assertEqual(len(proof), 43)
        self.assertEqual(self.db.calls[0][1]["p_proof_digest"], token_digest(proof))
        self.assertNotIn("123456", str(self.db.calls))

    def test_code_errors_use_public_contract(self):
        for code in ["CODE_MISMATCH", "CODE_EXPIRED", "VERIFICATION_INVALID"]:
            self.db.results["gomin_auth_verify_code"] = {"error": code}
            response = self.client.post("/api/v1/auth/email-verifications/confirm", json={
                "email": "member@example.com", "verification_id": self.request_id, "code": "123456"})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["error"]["code"], code)
            self.assertNotIn("123456", response.text)

    def test_signup_hashes_without_trimming_and_returns_cookie_and_member(self):
        response = self.client.post("/api/v1/auth/signup", json=self.payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"], self.member)
        params = self.db.calls[-1][1]
        self.assertEqual(params["p_email"], "member@example.com")
        self.assertEqual(params["p_name"], "사용자")
        self.assertTrue(verify_password(self.payload["password"], params["p_password_hash"]))
        self.assertFalse(verify_password(self.payload["password"].strip(), params["p_password_hash"]))
        self.assertNotIn(self.payload["password"], response.text)
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertIn("Max-Age=604800", cookie)
        token = self.client.cookies.get("gomin_session")
        self.assertEqual(params["p_session_digest"], token_digest(token))
        self.assertNotIn(token, str(params))
        repository = SimpleNamespace(renew_session=AsyncMock(return_value=self.member))
        self.app.dependency_overrides[get_auth_repository] = lambda: repository
        self.assertEqual(self.client.get("/api/v1/auth/me").json()["data"], self.member)
        repository.renew_session.assert_awaited_once_with(token_digest(token))

    def test_secure_cookie_in_https_configuration(self):
        self.app.dependency_overrides[signup_settings] = lambda: SETTINGS.model_copy(update={"auth_cookie_secure": True})
        response = self.client.post("/api/v1/auth/signup", json=self.payload)
        self.assertIn("Secure", response.headers["set-cookie"])

    def test_bad_signup_inputs_never_reach_rpc(self):
        for update in [{"name": " "}, {"name": "이" * 31}, {"email": "bad"},
                       {"password": "short"}, {"confirmation": "different"},
                       {"verification_proof": ""}, {"consents": []},
                       {"consents": [self.payload["consents"][0]]},
                       {"consents": [self.payload["consents"][0]] * 2},
                       {"consents": [{**c, "agreed": False} for c in self.payload["consents"]]}]:
            with self.subTest(update=list(update)):
                self.assertEqual(self.client.post("/api/v1/auth/signup", json={**self.payload, **update}).status_code, 422)
                self.assertEqual(self.db.calls, [])

    def test_stale_consent_version_does_not_hash_or_call_rpc(self):
        payload = {**self.payload, "consents": [{**c, "version": "old"} for c in self.payload["consents"]]}
        with patch("app.api.routes.signup.hash_password") as hashing:
            response = self.client.post("/api/v1/auth/signup", json=payload)
        self.assertEqual(response.status_code, 409)
        hashing.assert_not_called()
        self.assertEqual(self.db.calls, [])

    def test_failed_signup_never_issues_session_cookie(self):
        for code in ["EMAIL_EXISTS", "PROOF_INVALID"]:
            self.db.results["gomin_auth_signup"] = {"error": code}
            response = self.client.post("/api/v1/auth/signup", json=self.payload)
            self.assertEqual(response.status_code, 409 if code == "EMAIL_EXISTS" else 400)
            self.assertNotIn("set-cookie", response.headers)

    def test_database_error_is_sanitized(self):
        self.db.results["gomin_auth_begin_verification"] = RuntimeError("private-credential")
        response = self.request_code()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private-credential", response.text)
        self.mailer.send_verification_email.assert_not_awaited()

    def test_hmac_binds_email_request_code_and_signup_purpose(self):
        from uuid import UUID
        request_id = UUID(self.request_id)
        value = code_digest("k" * 32, request_id, "a@example.com", "123456")
        self.assertNotEqual(value, code_digest("k" * 32, uuid4(), "a@example.com", "123456"))
        self.assertNotEqual(value, code_digest("k" * 32, request_id, "b@example.com", "123456"))
        self.assertNotEqual(value, code_digest("k" * 32, request_id, "a@example.com", "654321"))


class LocalSeedTests(unittest.TestCase):
    def test_three_local_seed_passwords_match_shared_login_hasher(self):
        import re
        from pathlib import Path
        seed = (Path(__file__).resolve().parents[2] / "supabase/seed.sql").read_text()
        hashes = re.findall(r"scrypt\$32768\$8\$3\$[0-9a-f]+\$[0-9a-f]+", seed)
        self.assertEqual(len(hashes), 3)
        self.assertEqual(len(set(hashes)), 3)
        for encoded in hashes:
            self.assertTrue(verify_password("GominLocal!2026", encoded))
            self.assertFalse(verify_password("wrong-password", encoded))
