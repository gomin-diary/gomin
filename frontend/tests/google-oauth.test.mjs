import assert from 'node:assert/strict';
import { test } from 'node:test';
import { saveGoogleContext, readGoogleContext, clearGoogleContext, googleAuthorizationUrl, googleOAuthNotice } from '../src/lib/google-oauth.ts';
const store = () => {const values=new Map();return {getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};};
test('unknown and prototype error codes always return safe text',()=>{
  for(const code of ['__proto__','constructor','toString','unknown']) {
    assert.equal(googleOAuthNotice(code),'Google 인증에 실패했어요. 다시 시도해 주세요.');
  }
});
test('return route only admits exact allowed paths',()=>{
  for(const next of ['/talk','/collection','/settings','/']){
    const s=store();saveGoogleContext(s,'/login',next);assert.equal(readGoogleContext(s).next,next);
  }
  for(const next of ['https://evil.test','//evil.test','/talk?x=1','/settings/../evil','javascript:alert(1)']){
    const s=store();saveGoogleContext(s,'/signup',next);assert.deepEqual(readGoogleContext(s),{origin:'/signup',next:'/'});
  }
});
test('missing, damaged and inaccessible storage has safe defaults',()=>{
  assert.deepEqual(readGoogleContext(null),{origin:'/login',next:'/'});
  const s=store();s.setItem('gomin.google.navigation','broken');assert.deepEqual(readGoogleContext(s),{origin:'/login',next:'/'});
  const blocked={getItem(){throw Error()},setItem(){throw Error()},removeItem(){throw Error()}};
  assert.doesNotThrow(()=>saveGoogleContext(blocked,'/signup','/talk'));
  assert.deepEqual(readGoogleContext(blocked),{origin:'/login',next:'/'});
  assert.doesNotThrow(()=>clearGoogleContext(blocked));
});
test('cleanup clears routing and invalid origin is rejected',()=>{
  const s=store();saveGoogleContext(s,'//evil.test','/talk');assert.equal(readGoogleContext(s).origin,'/login');
  clearGoogleContext(s);assert.equal(readGoogleContext(s).next,'/');
});
test('same start implementation supports local and deployment URLs',()=>{
  for(const redirect of ['http://127.0.0.1:8000/api/v1/auth/google/callback','https://api.example.test/api/v1/auth/google/callback']) {
    const url='https://accounts.google.com/o/oauth2/v2/auth?redirect_uri='+encodeURIComponent(redirect);
    assert.equal(googleAuthorizationUrl(url),url);
  }
  for(const value of [undefined,'https://evil.test','https://accounts.google.com.evil.test/o/oauth2/v2/auth','http://accounts.google.com/o/oauth2/v2/auth','https://user@accounts.google.com/o/oauth2/v2/auth']) assert.throws(()=>googleAuthorizationUrl(value));
});
