import json
import unittest
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from app.config import Settings
from app import mail


def settings(**overrides):
    return Settings(_env_file=None, supabase_url='https://example.supabase.co',
                    supabase_secret_key='test-only', **overrides)


class MailTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = settings(resend_api_key='test-secret', resend_from_email='sender@gomin.today')
        self.requests = []

    async def send(self, handler, *, config=None, code='123456', key='verification/request-1'):
        async def transport(request):
            self.requests.append(request)
            return handler(request)
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            return await mail.ResendMailer(config or self.config, client).send_verification_email(
                'member@example.com', code, idempotency_key=key)

    async def test_https_payload_and_acceptance_id(self):
        result = await self.send(lambda r: httpx.Response(200, json={'id': 'email-1'}))
        self.assertEqual(result, 'email-1')
        request = self.requests[0]
        self.assertEqual(str(request.url), 'https://api.resend.com/emails')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.headers['Authorization'], 'Bearer test-secret')
        self.assertEqual(request.headers['Idempotency-Key'], 'verification/request-1')
        self.assertTrue(request.headers['User-Agent'])
        body = json.loads(request.content)
        self.assertEqual(body['from'], 'Gomin <sender@gomin.today>')
        self.assertEqual(body['to'], ['member@example.com'])
        self.assertIn('123456', body['text'])
        self.assertIn('3분', body['text'])

    async def test_html_and_stable_retry_key(self):
        async def transport(request):
            self.requests.append(request)
            return httpx.Response(200, json={'id': 'email-1'})
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            sender = mail.ResendMailer(self.config, client)
            for _ in range(2):
                await sender.send_email('member@example.com', '제목', '본문', html='<p>본문</p>',
                                        idempotency_key='same-request')
        self.assertEqual(self.requests[0].content, self.requests[1].content)
        self.assertEqual(self.requests[0].headers['Idempotency-Key'], 'same-request')
        self.assertEqual(self.requests[1].headers['Idempotency-Key'], 'same-request')
        self.assertEqual(json.loads(self.requests[0].content)['html'], '<p>본문</p>')

    async def test_confirmed_rejections_are_not_uncertain(self):
        for status in (400, 401, 403, 422, 429):
            with self.subTest(status=status):
                with self.assertRaises(mail.MailDeliveryError) as caught:
                    await self.send(lambda r: httpx.Response(status, json={'message': 'test-secret'}))
                self.assertFalse(caught.exception.delivery_uncertain)
                self.assertEqual(caught.exception.status_code, status)
                self.assertNotIn('test-secret', str(caught.exception))

    async def test_uncertain_errors_never_automatically_retry(self):
        for status in (409, 500, 503, 302):
            with self.subTest(status=status):
                self.requests.clear()
                with self.assertRaises(mail.MailDeliveryError) as caught:
                    await self.send(lambda r: httpx.Response(status, json={'message': 'test-secret'}))
                self.assertTrue(caught.exception.delivery_uncertain)
                self.assertEqual(len(self.requests), 1)

    async def test_timeout_is_uncertain_and_sanitized(self):
        def timeout(request):
            raise httpx.ReadTimeout('test-secret', request=request)
        with self.assertRaises(mail.MailDeliveryError) as caught:
            await self.send(timeout)
        self.assertTrue(caught.exception.delivery_uncertain)
        self.assertNotIn('test-secret', str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)
        self.assertEqual(len(self.requests), 1)

    async def test_connection_failure_is_confirmed_not_sent(self):
        def unavailable(request):
            raise httpx.ConnectError('test-secret', request=request)
        with self.assertRaises(mail.MailDeliveryError) as caught:
            await self.send(unavailable)
        self.assertFalse(caught.exception.delivery_uncertain)

    async def test_malformed_acceptance_is_uncertain(self):
        for body in ({}, {'id': ''}, [], {'id': 1}):
            with self.subTest(body=body):
                with self.assertRaises(mail.MailDeliveryError) as caught:
                    await self.send(lambda r: httpx.Response(200, json=body))
                self.assertTrue(caught.exception.delivery_uncertain)
        with self.assertRaises(mail.MailDeliveryError):
            await self.send(lambda r: httpx.Response(200, text='not json'))

    async def test_missing_or_invalid_configuration_never_sends(self):
        for config in (settings(), settings(resend_api_key='test-secret'),
                       settings(resend_api_key='test-secret', resend_from_email='invalid'),
                       settings(resend_api_key='test-secret', resend_from_email='sender@gomin.today',
                                resend_from_name='name\nBcc: victim@example.com')):
            with self.subTest(configured=bool(config.resend_from_email)):
                with self.assertRaises(mail.MailConfigurationError):
                    await self.send(lambda r: self.fail('must not send'), config=config)
        self.assertEqual(self.requests, [])

    async def test_invalid_code_or_key_never_sends(self):
        for code, key in (('12345', 'key'), ('１２３４５６', 'key'), ('1234567', 'key'),
                          ('123456', ''), ('123456', 'x' * 257), ('123456', 'key\n')):
            with self.subTest(code=code, key_length=len(key)):
                with self.assertRaises(ValueError):
                    await self.send(lambda r: self.fail('must not send'), code=code, key=key)
        self.assertEqual(self.requests, [])

    async def test_invalid_recipient_or_subject_never_sends(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: self.fail('must not send'))) as client:
            sender = mail.ResendMailer(self.config, client)
            for recipient, subject in (('invalid', 'Hi'), ('a@example.com,b@example.com', 'Hi'),
                                       ('a@example.com\n', 'Hi'), ('a@example.com', 'Hi\nBcc: b')):
                with self.subTest(recipient=recipient):
                    with self.assertRaises(ValueError):
                        await sender.send_email(recipient, subject, 'body', idempotency_key='key')

    def test_settings_mask_secret_and_reject_unsafe_timeout(self):
        self.assertNotIn('test-secret', repr(self.config))
        for value in (0, -1, 61, float('nan'), float('inf')):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    settings(resend_timeout_seconds=value)
        with patch.dict('os.environ', {'RESEND_API_KEY': 'test-secret',
                                      'RESEND_FROM_EMAIL': 'sender@gomin.today'}, clear=True):
            self.assertEqual(settings().resend_from_email, 'sender@gomin.today')

    def test_dependency_uses_resend(self):
        with patch('app.mail.get_settings', return_value=self.config):
            self.assertIsInstance(mail.get_mailer(), mail.ResendMailer)


if __name__ == '__main__':
    unittest.main()
