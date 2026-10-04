import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test, after } from 'node:test';
const { PGlite } = await import(process.env.PGLITE_MODULE);
const db = new PGlite();
after(() => db.close());
await db.exec('create role anon; create role authenticated; create role service_role bypassrls; grant usage on schema public to service_role;');
for (const name of ['20261002000000_login_sessions.sql','20261002010000_signup_verification.sql','20261004102555_google_oauth.sql','20261004110048_google_oauth_completion.sql']) {
  await db.exec(await readFile(new URL(`../migrations/${name}`, import.meta.url),'utf8'));
}
const b = n => Buffer.alloc(32,n);
const q = async (sql,args=[]) => (await db.query(sql,args)).rows;
const rpc = async (name,args) => (await q(`select gomin_auth_oauth_${name}(${args.map((_,i)=>`$${i+1}`).join(',')}) as result`,args))[0].result;
test('request is browser bound, one-use, expires, and newer start invalidates old request',async()=>{
  await rpc('begin',[b(1),b(2),'nonce','cipher']);
  assert.equal((await rpc('consume',[b(1),b(3)])).error,'OAUTH_REQUEST_INVALID');
  assert.equal((await rpc('consume',[b(1),b(2)])).nonce,'nonce');
  assert.equal((await rpc('consume',[b(1),b(2)])).error,'OAUTH_REQUEST_INVALID');
  await rpc('begin',[b(4),b(2),'new','cipher']);
  await rpc('begin',[b(5),b(2),'newer','cipher']);
  assert.equal((await rpc('consume',[b(4),b(2)])).error,'OAUTH_REQUEST_INVALID');
  await q("update oauth_authorization_requests set expires_at=clock_timestamp()-interval '1 second'");
  assert.equal((await rpc('consume',[b(5),b(2)])).error,'OAUTH_REQUEST_INVALID');
});
test('automatic linking preserves member and password, sub wins over changed email',async()=>{
  const [m]=await q("insert into members(email,name,password_hash) values('existing@example.test','기존 이름','original') returning id");
  const first=await rpc('login',['google-sub','existing@example.test',b(6)]);
  assert.equal(first.id,m.id); assert.equal(first.name,'기존 이름');
  assert.equal((await q('select password_hash from members where id=$1',[m.id]))[0].password_hash,'original');
  const again=await rpc('login',['google-sub','changed@example.test',b(7)]);
  assert.equal(again.id,m.id);
  assert.equal((await rpc('login',['other-sub','existing@example.test',b(8)])).error,'OAUTH_LINK_CONFLICT');
  assert.equal((await q('select count(*)::int n from member_consents where member_id=$1',[m.id]))[0].n,0);
});
test('pending signup is browser bound, atomic, version checked and one-use',async()=>{
  await rpc('pending_begin',[b(9),b(10),'new-sub','new@example.test',null]);
  assert.equal((await rpc('pending',[b(9),b(11)])).error,'OAUTH_PROOF_INVALID');
  const args=[b(9),b(10),'새 이름',b(12),'terms','privacy','terms','privacy'];
  assert.equal((await rpc('signup',[...args.slice(0,4),'old','privacy','terms','privacy'])).error,'CONSENT_VERSION_CHANGED');
  assert.equal((await q("select count(*)::int n from members where email='new@example.test'"))[0].n,0);
  const m=await rpc('signup',args);assert.equal(m.email,'new@example.test');
  assert.equal((await q('select password_hash from members where id=$1',[m.id]))[0].password_hash,null);
  assert.equal((await q('select count(*)::int n from member_consents where member_id=$1',[m.id]))[0].n,2);
  assert.equal((await q('select count(*)::int n from auth_sessions where member_id=$1',[m.id]))[0].n,1);
  assert.equal((await rpc('signup',args)).error,'OAUTH_PROOF_INVALID');
});
test('email race rolls back signup, expired and cancelled proofs rejected',async()=>{
  await rpc('pending_begin',[b(13),b(14),'race-sub','race@example.test','이름']);
  await q("insert into members(email,name,password_hash) values('race@example.test','기존','hash')");
  assert.equal((await rpc('signup',[b(13),b(14),'new',b(15),'t','p','t','p'])).error,'EMAIL_EXISTS');
  assert.equal((await q("select count(*)::int n from member_oauth_identities where subject='race-sub'"))[0].n,0);
  await rpc('cancel',[b(13),b(14)]);
  assert.equal((await rpc('pending',[b(13),b(14)])).error,'OAUTH_PROOF_INVALID');
  await rpc('pending_begin',[b(16),b(14),'expire-sub','expire@example.test','이름']);
  await q("update oauth_pending_actions set expires_at=clock_timestamp()-interval '1 second'");
  assert.equal((await rpc('pending',[b(16),b(14)])).error,'OAUTH_PROOF_INVALID');
});
test('service role only tables and functions',async()=>{
  for(const role of ['anon','authenticated']){
    assert.equal((await q("select has_table_privilege($1,'oauth_authorization_requests','SELECT') ok",[role]))[0].ok,false);
    assert.equal((await q("select has_function_privilege($1,'gomin_auth_oauth_consume(bytea,bytea)','EXECUTE') ok",[role]))[0].ok,false);
    assert.equal((await q("select has_function_privilege($1,'gomin_auth_oauth_complete(bytea,bytea,text,text,text,bytea,bytea)','EXECUTE') ok",[role]))[0].ok,false);
  }
});
test('completion rejects stale callbacks without replacing newer pending or issuing a session',async()=>{
  await rpc('begin',[b(30),b(31),'A','cipher']);
  await rpc('consume',[b(30),b(31)]);
  await rpc('cleanup',[]);
  // Consumed requests must survive cleanup until the in-flight callback finishes.
  assert.equal((await q('select count(*)::int n from oauth_authorization_requests where state_digest=$1',[b(30)]))[0].n,1);
  await rpc('begin',[b(32),b(31),'B','cipher']);
  await rpc('consume',[b(32),b(31)]);
  const newer=await rpc('complete',[b(32),b(31),'newer-sub','newer@example.test','이름',b(33),b(34)]);
  assert.equal(newer.new_member,true);
  const before=(await q('select count(*)::int n from auth_sessions'))[0].n;
  for(const [subject,email] of [['stale-sub','stale@example.test'],['google-sub','existing@example.test']]) {
    assert.equal((await rpc('complete',[b(30),b(31),subject,email,'이름',b(35),b(36)])).error,'OAUTH_REQUEST_INVALID');
  }
  assert.equal((await rpc('pending',[b(34),b(31)])).email,'newer@example.test');
  assert.equal((await q('select count(*)::int n from auth_sessions'))[0].n,before);
  assert.equal((await rpc('complete',[b(32),b(31),'newer-sub','newer@example.test','이름',b(33),b(34)])).error,'OAUTH_REQUEST_INVALID');
});
