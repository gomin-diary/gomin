import json
import time
import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
import httpx
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr
from app.auth.google_provider import GoogleProvider
from app.core.errors import AppError

class GoogleProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.settings = SimpleNamespace(google_oauth_client_id='test-client', google_oauth_client_secret=SecretStr('test-secret'),
            google_oauth_redirect_uri='http://127.0.0.1:8000/api/v1/auth/google/callback',
            auth_frontend_origin='http://127.0.0.1:3000', auth_oauth_encryption_key=SecretStr(Fernet.generate_key().decode()),auth_cookie_secure=False)
        self.claims = {'iss':'https://accounts.google.com','aud':'test-client','exp':int(time.time())+300,
            'iat':int(time.time()),'nonce':'nonce','sub':'google-user','email':'User@Example.test','email_verified':True,'name':'사용자'}
        self.kid='key1'; self.status=200; self.jwks_calls=0; self.jwks_body=None; self.token=None
        self.http=httpx.AsyncClient(transport=httpx.MockTransport(self.respond))
        self.provider=GoogleProvider(self.http,self.settings)
        self.addAsyncCleanup(self.http.aclose)
    def respond(self,request):
        if request.url.path.endswith('/certs'):
            self.jwks_calls+=1
            key=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
            return httpx.Response(200,json=self.jwks_body if self.jwks_body is not None else {'keys':[{**key,'kid':self.kid,'use':'sig','alg':'RS256'}]})
        body=parse_qs(request.content.decode())
        assert body['code']==['one-time-code'] and body['code_verifier']==['verifier']
        assert body['redirect_uri']==[self.settings.google_oauth_redirect_uri]
        return httpx.Response(self.status,json={'id_token':self.token or jwt.encode(self.claims,self.key,algorithm='RS256',headers={'kid':self.kid})})
    async def test_malformed_jwks_and_unsupported_algorithm_are_safe(self):
        for body in ({'keys': [None]}, {'keys': 'bad'}, {'keys': []}, {'keys': [{}]}, []):
            self.jwks_body=body; self.provider.expires=0
            with self.subTest(body=body), self.assertRaises(AppError) as caught:
                await self.provider.exchange_and_verify('one-time-code','verifier','nonce')
            self.assertEqual(caught.exception.code,'OAUTH_FAILED')
        self.token=jwt.encode(self.claims,'test-secret-with-sufficient-length',algorithm='HS256',headers={'kid':'key1'})
        self.jwks_calls=0
        with self.assertRaises(AppError):
            await self.provider.exchange_and_verify('one-time-code','verifier','nonce')
        self.assertEqual(self.jwks_calls,0)
    async def test_code_exchange_verifies_identity_and_cache(self):
        identity=await self.provider.exchange_and_verify('one-time-code','verifier','nonce')
        self.assertEqual(identity.email,'user@example.test'); self.assertEqual(identity.subject,'google-user')
        await self.provider.exchange_and_verify('one-time-code','verifier','nonce')
        self.assertEqual(self.jwks_calls,1)
    async def test_rejects_audience_nonce_issuer_expiry_and_unverified_mail(self):
        for field,value in [('aud','attacker'),('nonce','other'),('iss','https://evil.test'),('exp',int(time.time())-120),('email_verified',False),('sub',''),('email','bad')]:
            original=self.claims[field]; self.claims[field]=value
            with self.subTest(field=field),self.assertRaises(AppError):
                await self.provider.exchange_and_verify('one-time-code','verifier','nonce')
            self.claims[field]=original
    async def test_key_rotation_refreshes_jwks(self):
        await self.provider.exchange_and_verify('one-time-code','verifier','nonce')
        self.kid='key2';self.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        identity=await self.provider.exchange_and_verify('one-time-code','verifier','nonce')
        self.assertEqual(identity.subject,'google-user');self.assertEqual(self.jwks_calls,2)
    async def test_provider_error_and_wrong_signature_are_safe(self):
        self.status=400
        with self.assertRaises(AppError): await self.provider.exchange_and_verify('one-time-code','verifier','nonce')
        self.status=200
        await self.provider.exchange_and_verify('one-time-code','verifier','nonce')
        self.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        with self.assertRaises(AppError): await self.provider.exchange_and_verify('one-time-code','verifier','nonce')
    async def test_authorization_url_and_encrypted_verifier(self):
        query=parse_qs(urlparse(self.provider.authorization_url('state','nonce','challenge')).query)
        self.assertEqual(query['scope'],['openid email profile']);self.assertEqual(query['code_challenge_method'],['S256'])
        self.assertNotIn('access_type',query)
        encrypted=self.provider.encrypt_verifier('verifier')
        self.assertNotIn('verifier',encrypted);self.assertEqual(self.provider.decrypt_verifier(encrypted),'verifier')
