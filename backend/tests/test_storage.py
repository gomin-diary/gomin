import os
import unittest
from email import policy
from email.parser import BytesParser
from unittest.mock import patch
from uuid import UUID

import httpx

from app.core.config import Settings
from app.db.client import create_supabase_client
from app.storage import supabase as storage_module


class StorageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests = []
        self.handler = lambda r: httpx.Response(200, json={
            'Key': r.url.path.removeprefix('/storage/v1/object/'),
        })

        async def transport(request):
            self.requests.append(request)
            return self.handler(request)

        self.http = httpx.AsyncClient(transport=httpx.MockTransport(transport))
        self.addAsyncCleanup(self.http.aclose)
        self.config = Settings(_env_file=None, supabase_url='https://example.supabase.co',
                               supabase_secret_key='test-only-placeholder')
        self.storage = storage_module.SupabaseFileStorage(
            await create_supabase_client(self.config, self.http), self.config)

    def file_part(self, request):
        message = BytesParser(policy=policy.default).parsebytes(
            ('Content-Type: ' + request.headers['content-type'] + '\r\n\r\n').encode()
            + request.content)
        return next(part for part in message.iter_parts()
                    if part.get_param('name', header='content-disposition') == 'file')

    async def test_upload_stores_binary_with_unique_paths_and_no_overwrite(self):
        data = b'\x00\xffhello\r\n'
        first = await self.storage.upload(data, content_type='image/png')
        second = await self.storage.upload(data, content_type='image/png')
        self.assertEqual(first.bucket, 'gomin-files')
        UUID(first.path)
        self.assertNotEqual(first.path, second.path)
        request = self.requests[0]
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.url.path, '/storage/v1/object/gomin-files/' + first.path)
        self.assertEqual(request.headers['x-upsert'], 'false')
        part = self.file_part(request)
        self.assertEqual(part.get_payload(decode=True), data)
        self.assertEqual(part.get_content_type(), 'image/png')
        self.assertEqual(set(vars(first)), {'bucket', 'path'})
        self.assertFalse(self.http.is_closed)

    async def test_upload_defaults_to_binary_mime_and_uses_configured_bucket(self):
        config = self.config.model_copy(update={'storage_bucket': 'existing-files'})
        storage = storage_module.SupabaseFileStorage(
            await create_supabase_client(config, self.http), config)
        stored = await storage.upload(b'hello')
        self.assertEqual(stored.bucket, 'existing-files')
        self.assertEqual(self.file_part(self.requests[0]).get_content_type(),
                         'application/octet-stream')

    async def test_invalid_data_and_mime_never_contact_storage(self):
        for data in (b'', 'text', None):
            with self.subTest(data=data), self.assertRaises(ValueError):
                await self.storage.upload(data)
        for content_type in ('', 'text', 'text/plain\r\nx-secret: value', 'text/plain; charset=utf-8'):
            with self.subTest(content_type=content_type), self.assertRaises(ValueError):
                await self.storage.upload(b'hello', content_type=content_type)
        self.assertEqual(self.requests, [])

    async def test_maximum_size_is_checked_against_actual_bytes(self):
        config = self.config.model_copy(update={'storage_max_file_size_bytes': 3})
        storage = storage_module.SupabaseFileStorage(
            await create_supabase_client(config, self.http), config)
        await storage.upload(b'abc')
        self.requests.clear()
        with self.assertRaises(ValueError):
            await storage.upload(b'abcd')
        self.assertEqual(self.requests, [])

    async def test_provider_errors_are_sanitized_without_retry(self):
        for status in (400, 403, 404, 409, 413, 429, 500, 503):
            with self.subTest(status=status):
                self.requests.clear()
                self.handler = lambda r: httpx.Response(status, json={
                    'statusCode': str(status), 'error': 'Denied', 'message': 'test-secret',
                })
                with self.assertRaises(storage_module.StorageUploadError) as caught:
                    await self.storage.upload(b'hello')
                self.assertNotIn('test-secret', str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)
                self.assertEqual(len(self.requests), 1)

    async def test_transport_and_malformed_responses_are_safe(self):
        def timeout(request):
            raise httpx.ReadTimeout('test-secret', request=request)

        for handler in (timeout, lambda r: httpx.Response(200, json={}),
                        lambda r: httpx.Response(200, text='test-secret'),
                        lambda r: httpx.Response(200, json={'Key': 'wrong/test-secret'})):
            with self.subTest(handler=handler):
                self.requests.clear()
                self.handler = handler
                with self.assertRaises(storage_module.StorageUploadError) as caught:
                    await self.storage.upload(b'hello')
                self.assertNotIn('test-secret', str(caught.exception))
                self.assertEqual(len(self.requests), 1)

    def test_maximum_size_loads_from_environment_string(self):
        with patch.dict(os.environ, {'STORAGE_MAX_FILE_SIZE_BYTES': '10485760'}):
            settings = Settings(_env_file=None, supabase_url='https://example.supabase.co',
                                supabase_secret_key='test-only')
        self.assertEqual(settings.storage_max_file_size_bytes, 10485760)

    def test_bucket_configuration_cannot_escape_path(self):
        for bucket in ('', '../files', 'a/b', 'a\\b', 'a%2fb', 'a\n'):
            with self.subTest(bucket=bucket), self.assertRaises(ValueError):
                Settings(_env_file=None, supabase_url='https://example.supabase.co',
                         supabase_secret_key='test-only', storage_bucket=bucket)
