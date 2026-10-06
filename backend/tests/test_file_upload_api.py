import asyncio
import unittest
from uuid import UUID

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.files import router
from app.auth.session import COOKIE_NAME, get_auth_repository, get_auth_settings
from app.core.config import Settings
from app.core.exception_handlers import ERROR_RESPONSES, register_exception_handlers
from app.db.client import create_supabase_client, get_supabase
from app.storage.dependencies import get_storage_settings


OWNER = UUID('12345678-1234-5678-1234-567812345678')


class Repository:
    async def renew_session(self, digest):
        return {'id': OWNER, 'name': '테스트', 'email': 'member@example.test'}


class FileUploadApiTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.handler = lambda r: httpx.Response(200, json={
            'url': r.url.path.removeprefix('/storage/v1') + '?token=test-token',
        })

        async def transport(request):
            self.requests.append(request)
            return self.handler(request)

        self.http = httpx.AsyncClient(transport=httpx.MockTransport(transport))
        self.addCleanup(lambda: asyncio.run(self.http.aclose()))
        self.config = Settings(_env_file=None, supabase_url='https://example.supabase.co',
                               supabase_secret_key='test-only-placeholder', auth_cookie_secure=False)
        self.db = asyncio.run(create_supabase_client(self.config, self.http))
        app = FastAPI(responses=ERROR_RESPONSES)
        register_exception_handlers(app)
        app.include_router(router)
        app.dependency_overrides[get_storage_settings] = lambda: self.config
        app.dependency_overrides[get_auth_settings] = lambda: self.config
        app.dependency_overrides[get_auth_repository] = Repository
        app.dependency_overrides[get_supabase] = lambda: self.db
        self.app = app
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.client.cookies.set(COOKIE_NAME, 'a' * 43)

    def mint(self, **values):
        return self.client.post('/api/v1/files/upload-url', json={
            'filename': '고민.pdf', 'size': 100, 'content_type': 'application/pdf', **values,
        })

    def test_authenticated_url_has_unique_member_path_and_safe_cookie(self):
        first = self.mint()
        self.assertEqual(first.status_code, 200, first.text)
        data = first.json()['data']
        self.assertEqual(data['bucket'], 'gomin-files')
        self.assertTrue(data['path'].startswith(str(OWNER) + '/'))
        self.assertNotIn('고민', data['path'])
        UUID(data['path'].split('/')[1])
        self.assertNotEqual(data['path'], self.mint().json()['data']['path'])
        self.assertEqual(data['expires_in'], 7200)
        self.assertEqual(data['max_file_size_bytes'], 10485760)
        self.assertEqual(first.headers['cache-control'], 'no-store')
        self.assertIn('HttpOnly', first.headers['set-cookie'])
        self.assertNotIn('test-only-placeholder', first.text)
        self.assertEqual(self.mint(size=10485760).status_code, 200)

    def test_no_session_never_contacts_storage(self):
        self.client.cookies.clear()
        response = self.mint()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error']['code'], 'UNAUTHORIZED')
        self.assertEqual(self.requests, [])

    def test_invalid_inputs_and_size_never_contact_storage(self):
        for values in ({'filename': ''}, {'filename': '../secret'}, {'filename': 'a\\b'},
                       {'filename': 'a\n'}, {'filename': 'x' * 256}, {'size': 0}, {'size': -1},
                       {'size': True}, {'size': 1.5}, {'size': '2'}, {'content_type': ''},
                       {'content_type': 'text/plain\n'}, {'content_type': 'image/*'},
                       {'content_type': 'text/plain; charset=UTF-8'}, {'path': '../other'}):
            with self.subTest(values=values):
                self.assertEqual(self.mint(**values).status_code, 422)
        response = self.mint(size=10485761)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()['error']['code'], 'FILE_TOO_LARGE')
        self.assertEqual(self.requests, [])

    def test_disallowed_origin_never_contacts_storage(self):
        response = self.client.post('/api/v1/files/upload-url',
                                    headers={'Origin': 'https://evil.example.test'},
                                    json={'filename': 'a', 'size': 1, 'content_type': 'text/plain'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.requests, [])
        response = self.client.post('/api/v1/files/upload-url',
                                    headers={'Origin': 'http://127.0.0.1:3000'},
                                    json={'filename': 'a', 'size': 1, 'content_type': 'text/plain'})
        self.assertEqual(response.status_code, 200)

    def test_signing_error_uses_safe_common_failure(self):
        self.handler = lambda r: httpx.Response(503, json={'message': 'test-secret'})
        response = self.mint()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'STORAGE_UNAVAILABLE')
        self.assertIsNone(response.json()['data'])
        self.assertNotIn('test-secret', response.text)

    def test_contract_is_in_openapi(self):
        operation = self.app.openapi()['paths']['/api/v1/files/upload-url']['post']
        self.assertIn('200', operation['responses'])
        self.assertIn('422', operation['responses'])
        self.assertEqual(operation['responses']['413']['content']['application/json']['schema']['$ref'],
                         '#/components/schemas/ApiFailure')
