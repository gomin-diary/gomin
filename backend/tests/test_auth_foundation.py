import secrets
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.sessions import router
from app.auth.crypto import code_digest
from app.auth.security import hash_password, new_session_token, token_digest, verify_password
from app.auth.session import COOKIE_NAME, get_auth_repository, get_auth_settings
from app.core.config import Settings
from app.core.errors import AppError
from app.core.exception_handlers import register_exception_handlers


class SessionRepository:
    def __init__(self):
        self.member = {"id": str(uuid4()), "email": "member@example.com", "name": "회원"}
        self.sessions = {}
        self.unavailable = False

    def issue(self):
        token = new_session_token()
        self.sessions[token_digest(token)] = datetime.now(timezone.utc) + timedelta(days=7)
        return token

    async def renew_session(self, digest):
        if self.unavailable:
            raise AppError(503, "SERVICE_UNAVAILABLE", "인증 서비스를 일시적으로 이용할 수 없습니다.")
        expires = self.sessions.get(digest)
        if expires is None or expires <= datetime.now(timezone.utc):
            return None
        self.sessions[digest] = datetime.now(timezone.utc) + timedelta(days=7)
        return self.member

    async def delete_session(self, digest):
        if self.unavailable:
            raise AppError(503, "SERVICE_UNAVAILABLE", "인증 서비스를 일시적으로 이용할 수 없습니다.")
        self.sessions.pop(digest, None)


class AuthFoundationTests(unittest.TestCase):
    def setUp(self):
        self.repository = SessionRepository()
        self.settings = Settings(_env_file=None, supabase_url="https://db.example.com",
                                 supabase_secret_key=secrets.token_urlsafe(32))
        self.app = FastAPI()
        register_exception_handlers(self.app)
        self.app.include_router(router)
        self.app.dependency_overrides[get_auth_repository] = lambda: self.repository
        self.app.dependency_overrides[get_auth_settings] = lambda: self.settings
        self.client = TestClient(self.app, base_url="https://frontend.example.com")
        self.addCleanup(self.client.close)

    def attach(self, token):
        self.client.cookies.set(COOKIE_NAME, token)

    def test_member_lookup_renews_session_and_secure_cookie(self):
        token = self.repository.issue()
        self.repository.sessions[token_digest(token)] = datetime.now(timezone.utc) + timedelta(minutes=1)
        self.attach(token)
        response = self.client.get("/api/v1/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], self.repository.member)
        self.assertGreater(self.repository.sessions[token_digest(token)],
                           datetime.now(timezone.utc) + timedelta(days=6))
        cookie = response.headers["set-cookie"]
        for attribute in ("HttpOnly", "Secure", "SameSite=lax", "Max-Age=604800", "Path=/"):
            self.assertIn(attribute, cookie)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_local_cookie_setting_is_shared(self):
        self.settings = self.settings.model_copy(update={"auth_cookie_secure": False})
        self.attach(self.repository.issue())
        response = self.client.get("/api/v1/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Secure", response.headers["set-cookie"])

    def test_missing_malformed_unknown_and_expired_sessions_are_rejected(self):
        expired = self.repository.issue()
        self.repository.sessions[token_digest(expired)] = datetime.now(timezone.utc) - timedelta(seconds=1)
        for token in (None, "invalid", new_session_token(), expired):
            with self.subTest(kind="missing" if token is None else "invalid"):
                self.client.cookies.clear()
                if token is not None:
                    self.attach(token)
                response = self.client.get("/api/v1/auth/me")
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")
                self.assertNotIn("set-cookie", response.headers)

    def test_logout_revokes_only_current_session_and_is_idempotent(self):
        token, other = self.repository.issue(), self.repository.issue()
        self.attach(token)
        response = self.client.post("/api/v1/auth/logout")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
        self.assertNotIn(token_digest(token), self.repository.sessions)
        self.assertIn(token_digest(other), self.repository.sessions)
        self.attach(token)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 200)
        self.client.cookies.clear()
        self.attach(other)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 200)

    def test_database_failure_does_not_refresh_cookie(self):
        self.attach(self.repository.issue())
        self.repository.unavailable = True
        response = self.client.get("/api/v1/auth/me")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("set-cookie", response.headers)

    def test_feature_endpoints_are_separate_from_session_router(self):
        for path in ("login", "signup", "email-verifications"):
            self.assertEqual(self.client.post(f"/api/v1/auth/{path}").status_code, 404)

    def test_shared_password_hasher_preserves_whitespace_and_salts(self):
        password = secrets.token_urlsafe(16) + " "
        first, second = hash_password(password), hash_password(password)
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password(password, first))
        self.assertFalse(verify_password(password.strip(), first))
        self.assertFalse(verify_password(password, "invalid"))

    def test_email_code_digest_is_bound_to_request_email_and_purpose(self):
        key, code, request_id = secrets.token_urlsafe(32), "123456", uuid4()
        digest = code_digest(key, request_id, "member@example.com", code)
        self.assertNotEqual(digest, code_digest(key, uuid4(), "member@example.com", code))
        self.assertNotEqual(digest, code_digest(key, request_id, "other@example.com", code))
        self.assertNotEqual(digest, token_digest(code))


if __name__ == "__main__":
    unittest.main()
