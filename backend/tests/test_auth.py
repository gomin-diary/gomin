import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.auth import router
from app.api.routes.sessions import router as sessions_router
from app.auth.session import COOKIE_NAME, get_auth_repository, get_auth_settings
from app.auth.security import hash_password, token_digest, verify_password
from app.core.config import Settings
from app.core.errors import AppError
from app.core.exception_handlers import ERROR_RESPONSES, register_exception_handlers


class Repository:
    """Isolated API tests; PostgreSQL's atomic locking needs separate verification."""
    def __init__(self):
        self.member = {"id": str(uuid4()), "email": "member@example.test", "name": "테스트",
                       "password_hash": hash_password(" password 123! ")}
        self.sessions = {}
        self.failure = False

    def check(self):
        if self.failure:
            raise AppError(503, "SERVICE_UNAVAILABLE", "인증 서비스를 일시적으로 이용할 수 없습니다.")

    async def find_member(self, email):
        self.check()
        return self.member if email == self.member["email"] else None

    async def create_session(self, member_id, digest):
        self.check()
        self.sessions[digest] = datetime.now(timezone.utc) + timedelta(days=7)

    async def renew_session(self, digest):
        self.check()
        if digest not in self.sessions or self.sessions[digest] <= datetime.now(timezone.utc):
            return None
        self.sessions[digest] = datetime.now(timezone.utc) + timedelta(days=7)
        return self.member

    async def delete_session(self, digest):
        self.check()
        self.sessions.pop(digest, None)


class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repository = Repository()

    def setUp(self):
        self.repository.sessions.clear()
        self.repository.failure = False
        self.settings = Settings(_env_file=None, supabase_url="https://example.supabase.co",
                                 supabase_secret_key="test-only-placeholder", auth_cookie_secure=False)
        self.app = FastAPI(responses=ERROR_RESPONSES)
        register_exception_handlers(self.app)
        self.app.include_router(router)
        self.app.include_router(sessions_router)
        self.app.dependency_overrides[get_auth_repository] = lambda: self.repository
        self.app.dependency_overrides[get_auth_settings] = lambda: self.settings
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def login(self, client=None, **values):
        return (client or self.client).post("/api/v1/auth/login", json={
            "email": "member@example.test", "password": " password 123! ", **values,
        })

    def test_normalized_login_uses_digest_and_safe_cookie(self):
        response = self.login(email="  MEMBER@EXAMPLE.TEST  ")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.json()["data"]["name"], "테스트")
        self.assertNotIn("password", response.text)
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertIn("Max-Age=604800", cookie)
        self.assertEqual(response.headers["cache-control"], "no-store")
        token = self.client.cookies.get(COOKIE_NAME)
        self.assertIn(token_digest(token), self.repository.sessions)
        self.assertNotIn(token, self.repository.sessions)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 200)

    def test_google_only_member_cannot_password_login(self):
        original = self.repository.member['password_hash']
        try:
            self.repository.member['password_hash'] = None
            response = self.login()
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()['error']['code'], 'INVALID_CREDENTIALS')
            self.assertNotIn('set-cookie', response.headers)
        finally:
            self.repository.member['password_hash'] = original

    def test_https_secure_is_default(self):
        self.settings.auth_cookie_secure = True
        self.assertIn("Secure", self.login().headers["set-cookie"])
        self.assertTrue(Settings(_env_file=None, supabase_url="https://example.supabase.co",
                                 supabase_secret_key="test-only-placeholder").auth_cookie_secure)

    def test_unknown_email_and_wrong_password_have_identical_error(self):
        missing = self.login(email="unknown@example.test")
        wrong = self.login(password="incorrect")
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.json(), wrong.json())
        self.assertEqual(missing.json()["error"]["code"], "INVALID_CREDENTIALS")
        self.assertFalse(self.repository.sessions)
        self.assertNotIn("set-cookie", wrong.headers)

    def test_password_whitespace_is_significant(self):
        self.assertEqual(self.login(password="password 123!").status_code, 401)
        self.assertEqual(self.login().status_code, 200)

    def test_required_fields_and_email_are_validated_without_echo(self):
        for payload in ({}, {"email": "invalid", "password": "private-value"},
                        {"email": "member@example.test", "password": ""}):
            response = self.client.post("/api/v1/auth/login", json=payload)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("private-value", response.text)
        self.assertFalse(self.repository.sessions)

    def test_session_renewal_and_expiration(self):
        self.login()
        digest = token_digest(self.client.cookies.get(COOKIE_NAME))
        self.repository.sessions[digest] = datetime.now(timezone.utc) + timedelta(minutes=1)
        response = self.client.get("/api/v1/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(self.repository.sessions[digest], datetime.now(timezone.utc) + timedelta(days=6))
        self.assertIn("Max-Age=604800", response.headers["set-cookie"])
        self.repository.sessions[digest] = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)
        self.assertLess(self.repository.sessions[digest], datetime.now(timezone.utc))

    def test_missing_malformed_and_forged_session_rejected(self):
        for token in (None, "invalid", "a" * 43):
            self.client.cookies.clear()
            if token:
                self.client.cookies.set(COOKIE_NAME, token)
            response = self.client.get("/api/v1/auth/me")
            self.assertEqual(response.status_code, 401)
        self.assertFalse(self.repository.sessions)

    def test_logout_preserves_other_session_and_deleted_token_cannot_return(self):
        other = TestClient(self.app)
        self.addCleanup(other.close)
        self.login()
        token = self.client.cookies.get(COOKIE_NAME)
        self.login(other)
        self.assertEqual(len(self.repository.sessions), 2)
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 200)
        self.assertEqual(len(self.repository.sessions), 1)
        self.assertEqual(other.get("/api/v1/auth/me").status_code, 200)
        self.client.cookies.set(COOKIE_NAME, token)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)
        self.assertEqual(len(self.repository.sessions), 1)

    def test_logout_is_idempotent(self):
        response = self.client.post("/api/v1/auth/logout")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_service_failure_does_not_issue_cookie(self):
        self.repository.failure = True
        response = self.login()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("set-cookie", response.headers)


class PasswordTests(unittest.TestCase):
    def test_hash_salts_and_bad_format(self):
        first = hash_password("test-password")
        second = hash_password("test-password")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("test-password", first))
        self.assertFalse(verify_password("wrong", first))
        for encoded in ("broken", first.replace("32768", "999999999"), first + "00"):
            self.assertFalse(verify_password("test-password", encoded))


if __name__ == "__main__":
    unittest.main()
