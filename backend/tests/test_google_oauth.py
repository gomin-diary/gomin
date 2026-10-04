import unittest
from urllib.parse import urlparse, parse_qs
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient
from cryptography.fernet import Fernet
from app.api.routes.google_oauth import router, get_oauth_repository, get_google_provider
from app.auth.google_provider import GoogleIdentity, GoogleProvider
from app.auth.session import get_auth_settings
from app.core.config import Settings
from app.core.errors import AppError
from app.core.exception_handlers import register_exception_handlers

class Repo:
    def __init__(self):
        self.requests={};self.pending_rows={};self.member=None;self.fail=False
    async def call(self,name,params):
        if self.fail:raise AppError(503,'SERVICE_UNAVAILABLE','unavailable')
        if name=='cleanup':return {}
        if name=='begin':
            self.requests={key:row for key,row in self.requests.items() if row['p_binding']!=params['p_binding']}
            self.requests[params['p_state']]=params;return {}
        if name=='consume':
            row=self.requests.get(params['p_state'])
            if not row or row['p_binding']!=params['p_binding'] or row.get('consumed'):raise AppError(400,'OAUTH_REQUEST_INVALID','invalid')
            row['consumed']=True
            return {'nonce':row['p_nonce'],'verifier':row['p_verifier']}
        if name=='complete':
            row=self.requests.get(params['p_state'])
            if not row or not row.get('consumed') or row['p_binding']!=params['p_binding']:raise AppError(400,'OAUTH_REQUEST_INVALID','invalid')
            del self.requests[params['p_state']]
            if self.member:return self.member
            self.pending_rows[params['p_proof']]=params
            return {'new_member':True}
        if name=='login':return self.member or {'new_member':True}
        if name=='pending_begin':
            self.pending_rows[params['p_proof']]=params;return {}
        if name in ('pending','signup','cancel'):
            row=self.pending_rows.get(params['p_proof'])
            if not row or row['p_binding']!=params['p_binding']:raise AppError(400,'OAUTH_PROOF_INVALID','invalid')
            if name=='cancel':del self.pending_rows[params['p_proof']];return {}
            if name=='pending':return {'email':row['p_email'],'profile_name':row['p_name'],'expires_at':'2099-01-01T00:00:00Z'}
            del self.pending_rows[params['p_proof']]
            return {'id':str(uuid4()),'email':row['p_email'],'name':params['p_name']}
        raise AssertionError(name)
class Provider:
    def __init__(self,settings):
        self.real=GoogleProvider(None,settings);self.fail=False
    def validate_config(self):self.real.validate_config()
    def authorization_url(self,*args):return self.real.authorization_url(*args)
    def encrypt_verifier(self,*args):return self.real.encrypt_verifier(*args)
    def decrypt_verifier(self,*args):return self.real.decrypt_verifier(*args)
    async def exchange_and_verify(self,*args):
        if self.fail:raise AppError(400,'OAUTH_FAILED','safe')
        return GoogleIdentity('sub','member@example.test','이름')
class OAuthRouteTests(unittest.TestCase):
    def setUp(self):
        self.settings=Settings(_env_file=None,supabase_url='https://example.supabase.co',supabase_secret_key='test-placeholder',
            google_oauth_client_id='client',google_oauth_client_secret='secret',
            google_oauth_redirect_uri='http://127.0.0.1:8000/api/v1/auth/google/callback',
            auth_frontend_origin='http://127.0.0.1:3000',auth_oauth_encryption_key=Fernet.generate_key().decode(),auth_cookie_secure=False)
        self.repo=Repo();self.provider=Provider(self.settings)
        app=FastAPI();register_exception_handlers(app);app.include_router(router)
        self.logged_queries=[]
        @app.middleware('http')
        async def observe_access_log_scope(request, call_next):
            response=await call_next(request)
            self.logged_queries.append(request.scope['query_string'])
            return response
        app.dependency_overrides[get_auth_settings]=lambda:self.settings
        app.dependency_overrides[get_oauth_repository]=lambda:self.repo
        app.dependency_overrides[get_google_provider]=lambda:self.provider
        self.client=TestClient(app,base_url='http://127.0.0.1:8000',raise_server_exceptions=False)
        self.addCleanup(self.client.close)
    def begin(self):
        response=self.client.get('/api/v1/auth/google/start',follow_redirects=False)
        self.assertEqual(response.status_code,302)
        self.assertIn('HttpOnly',response.headers['set-cookie'])
        return parse_qs(urlparse(response.headers['location']).query)['state'][0]
    def callback(self,state,**params):
        return self.client.get('/api/v1/auth/google/callback',params={'state':state,'code':'code',**params},follow_redirects=False)
    def test_login_sets_session_fixed_result_and_cannot_replay(self):
        self.repo.member={'id':str(uuid4()),'email':'member@example.test','name':'기존'}
        state=self.begin();r=self.callback(state)
        self.assertIn('result=login',r.headers['location']);self.assertIn('gomin_session=',r.headers['set-cookie'])
        self.assertEqual(urlparse(r.headers['location']).path,'/auth/google/result')
        self.assertIn('result=error',self.callback(state).headers['location'])
    def test_callback_query_is_removed_from_access_log_scope(self):
        response=self.callback(self.begin())
        self.assertIn('result=signup',response.headers['location'])
        self.assertEqual(self.logged_queries[-1],b'')
    def test_new_start_during_google_http_blocks_old_callback_completion(self):
        state=self.begin()
        async def newer_start(*args):
            old=next(iter(self.repo.requests.values()))
            await self.repo.call('begin',{'p_state':'newer-state','p_binding':old['p_binding'],'p_nonce':'newer','p_verifier':'cipher'})
            return GoogleIdentity('sub','member@example.test','이름')
        self.provider.exchange_and_verify=newer_start
        response=self.callback(state)
        self.assertIn('OAUTH_REQUEST_INVALID',response.headers['location'])
        self.assertNotIn('gomin_session=',response.headers.get('set-cookie',''))
        self.assertEqual(self.repo.pending_rows,{})
    def test_signup_requires_browser_origin_csrf_and_consents(self):
        self.callback(self.begin())
        pending=self.client.get('/api/v1/auth/google/pending').json()['data']
        body={'name':'새 이름','csrf_token':pending['csrf_token'],'consents':[
            {'type':'terms_of_service','version':'dev-2026-10-02','agreed':True},
            {'type':'privacy_collection','version':'dev-2026-10-02','agreed':True}]}
        path='/api/v1/auth/google/signup'
        self.assertEqual(self.client.post(path,json=body).status_code,403)
        self.assertEqual(self.client.post(path,json={**body,'csrf_token':'wrong'},headers={'Origin':'http://127.0.0.1:3000'}).status_code,403)
        r=self.client.post(path,json=body,headers={'Origin':'http://127.0.0.1:3000'})
        self.assertEqual(r.status_code,201);self.assertEqual(r.json()['data']['name'],'새 이름')
        self.assertIn('gomin_session=',r.headers['set-cookie'])
        self.assertEqual(self.client.get('/api/v1/auth/google/pending').status_code,400)
    def test_cancellation_and_provider_failure_issue_no_session(self):
        r=self.callback(self.begin(),error='access_denied')
        self.assertIn('result=cancelled',r.headers['location']);self.assertNotIn('gomin_session=',r.headers.get('set-cookie',''))
        self.provider.fail=True
        r=self.callback(self.begin());self.assertIn('result=error',r.headers['location'])
        self.assertNotIn('gomin_session=',r.headers.get('set-cookie',''))
    def test_forged_state_or_missing_binding_rejected(self):
        state=self.begin();self.client.cookies.clear()
        r=self.callback(state);self.assertIn('result=error',r.headers['location'])
        r=self.callback('forged');self.assertIn('result=error',r.headers['location'])
    def test_unconfigured_and_db_failure_are_safe(self):
        self.settings.google_oauth_client_id=''
        self.assertEqual(self.client.get('/api/v1/auth/google/start').status_code,503)
        self.settings.google_oauth_client_id='client';self.repo.fail=True
        self.assertEqual(self.client.get('/api/v1/auth/google/start').status_code,503)
    def test_start_json_prepares_cookie_and_google_url_without_navigation(self):
        response=self.client.get('/api/v1/auth/google/start?response=json',follow_redirects=False)
        self.assertEqual(response.status_code,200)
        url=response.json()['data']['authorization_url']
        self.assertEqual(urlparse(url).hostname,'accounts.google.com')
        self.assertIn('state',parse_qs(urlparse(url).query))
        self.assertIn('HttpOnly',response.headers['set-cookie'])
