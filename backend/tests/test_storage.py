import unittest
import os
from unittest.mock import patch
from uuid import UUID

import httpx

from app.core.config import Settings
from app.db.client import create_supabase_client
from app.storage.supabase import StorageSigningError, SupabaseFileStorage


OWNER = UUID('12345678-1234-5678-1234-567812345678')


class StorageTests(unittest.IsolatedAsyncioTestCase):
    def test_maximum_size_loads_from_environment_string(self):
        with patch.dict(os.environ, {'STORAGE_MAX_FILE_SIZE_BYTES': '10485760'}):
            settings = Settings(_env_file=None, supabase_url='https://example.supabase.co',
                                supabase_secret_key='test-only')
        self.assertEqual(settings.storage_max_file_size_bytes, 10485760)

    async def asyncSetUp(self):
        self.requests = []
        self.handler = lambda r: httpx.Response(200, json={
            'url': r.url.path.removeprefix('/storage/v1') + '?token=test-token',
        })

        async def transport(request):
            self.requests.append(request)
            return self.handler(request)

        self.http = httpx.AsyncClient(transport=httpx.MockTransport(transport))
        self.addAsyncCleanup(self.http.aclose)
        config = Settings(_env_file=None, supabase_url='https://example.supabase.co',
                          supabase_secret_key='test-only-placeholder')
        self.storage = SupabaseFileStorage(await create_supabase_client(config, self.http), config)

    async def test_issues_unique_owner_paths_without_upsert_and_maps_sdk_url(self):
        first = await self.storage.create_upload_url(OWNER)
        second = await self.storage.create_upload_url(OWNER)
        self.assertEqual(first.bucket, 'gomin-files')
        self.assertTrue(first.path.startswith(str(OWNER) + '/'))
        UUID(first.path.split('/')[1])
        self.assertNotEqual(first.path, second.path)
        request = self.requests[0]
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.url.path, '/storage/v1/object/upload/sign/gomin-files/' + first.path)
        self.assertNotEqual(request.headers.get('x-upsert'), 'true')
        self.assertEqual(first.upload_url,
                         'https://example.supabase.co' + request.url.path + '?token=test-token')
        self.assertEqual(first.expires_in, 7200)
        self.assertNotIn('test-token', repr(first))
        self.assertFalse(self.http.is_closed)

    async def test_provider_errors_are_sanitized_without_retry(self):
        for status in (400, 403, 404, 409, 413, 429, 500, 503):
            with self.subTest(status=status):
                self.requests.clear()
                self.handler = lambda r: httpx.Response(status, json={
                    'statusCode': str(status), 'error': 'Denied', 'message': 'test-secret',
                })
                with self.assertRaises(StorageSigningError) as caught:
                    await self.storage.create_upload_url(OWNER)
                self.assertNotIn('test-secret', str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)
                self.assertEqual(len(self.requests), 1)

    async def test_transport_and_malformed_responses_are_safe(self):
        def timeout(request):
            raise httpx.ReadTimeout('test-secret', request=request)

        for handler in (timeout, lambda r: httpx.Response(200, json={}),
                        lambda r: httpx.Response(200, text='test-secret'),
                        lambda r: httpx.Response(200, json={'url': '/object?missing-token'}),
                        lambda r: httpx.Response(200, json={'url': '/wrong?token=test-secret'})):
            with self.subTest(handler=handler):
                self.handler = handler
                with self.assertRaises(StorageSigningError) as caught:
                    await self.storage.create_upload_url(OWNER)
                self.assertNotIn('test-secret', str(caught.exception))

    async def test_bucket_configuration_cannot_escape_path(self):
        for bucket in ('', '../files', 'a/b', 'a\\b', 'a%2fb', 'a\n'):
            with self.subTest(bucket=bucket), self.assertRaises(ValueError):
                Settings(_env_file=None, supabase_url='https://example.supabase.co',
                         supabase_secret_key='test-only', storage_bucket=bucket)
