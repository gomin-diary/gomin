import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { test } from 'node:test';

// Optional test-only PostgreSQL runtime; no real environment files or credentials.
const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite');
const db = new PGlite();
await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
 grant usage on schema public to service_role;`);
for (const file of ['20261002000000_login_sessions.sql', '20261002010000_signup_verification.sql']) {
  await db.exec(await readFile(new URL(`../migrations/${file}`, import.meta.url), 'utf8'));
}
const bytes = (digit) => `\\x${digit.repeat(64)}`;
const code = bytes('a'), proof = bytes('b');
const query = async (sql, args = []) => (await db.query(sql, args.map(value => typeof value === 'string' && value.startsWith('\\x') ? Buffer.from(value.slice(2), 'hex') : value))).rows;
const rpc = async (name, args) => (await query(`select public.gomin_auth_${name}(${args.map((_, i) => `$${i+1}`).join(',')}) as result`, args))[0].result;
const email = () => `${randomUUID()}@example.com`;
async function start(address = email()) {
  const id = randomUUID();
  await rpc('begin_verification', [id, address, code]);
  return { id, address };
}
async function verified(address = email()) {
  const state = await start(address);
  await rpc('finish_delivery', [state.id, true]);
  // Each proof digest is unique; production creates a new cryptographic token.
  state.proof = `\\x${state.id.replaceAll('-', '').repeat(2)}`;
  await rpc('verify_code', [state.id, state.address, code, state.proof]);
  return state;
}
const signup = (state, session = bytes('c'), terms = 'dev-2026-10-02') => rpc('signup', [
  state.address, '사용자', 'test-password-hash', state.proof ?? proof, session,
  terms, 'dev-2026-10-02', 'dev-2026-10-02', 'dev-2026-10-02',
]);

test('pending cannot be confirmed; accepted mail starts 3 minutes, wrong code and expiry rejected', async () => {
  const state = await start();
  assert.equal((await rpc('verify_code', [state.id, state.address, code, proof])).error, 'VERIFICATION_INVALID');
  const result = await rpc('finish_delivery', [state.id, true]);
  assert.ok(Date.parse(result.expires_at) - Date.now() > 170000);
  assert.equal((await rpc('verify_code', [state.id, state.address, bytes('f'), proof])).error, 'CODE_MISMATCH');
  await query(`update public.email_verifications set expires_at=clock_timestamp()-interval '1 second' where id=$1`, [state.id]);
  assert.equal((await rpc('verify_code', [state.id, state.address, code, proof])).error, 'CODE_EXPIRED');
});

test('resend invalidates old code/proof and late delivery cannot reactivate it', async () => {
  const first = await start();
  const second = await start(first.address);
  assert.equal((await rpc('finish_delivery', [first.id, true])).error, 'VERIFICATION_INVALID');
  assert.equal((await query('select status,code_hmac,proof_digest from public.email_verifications where id=$1', [first.id]))[0].status, 'invalidated');
  await rpc('finish_delivery', [second.id, true]);
  assert.equal((await rpc('verify_code', [first.id, first.address, code, proof])).error, 'VERIFICATION_INVALID');
  await rpc('verify_code', [second.id, second.address, code, proof]);
  assert.equal((await rpc('verify_code', [second.id, second.address, code, bytes('e')])).error, 'VERIFICATION_INVALID');
  await start(first.address);
  assert.equal((await signup({ address:first.address, proof })).error, 'PROOF_INVALID');
});

test('proof is bound to email, expires after 30 minutes and cannot be forged', async () => {
  const state = await verified();
  const row = (await query('select * from public.email_verifications where id=$1', [state.id]))[0];
  assert.ok(Date.parse(row.expires_at) - Date.now() > 1790000);
  assert.equal(row.code_hmac, null);
  assert.equal((await signup({ ...state, address: email() })).error, 'PROOF_INVALID');
  assert.equal((await signup({ ...state, proof:bytes('f') })).error, 'PROOF_INVALID');
  await query(`update public.email_verifications set expires_at=clock_timestamp()-interval '1 second' where id=$1`, [state.id]);
  assert.equal((await signup(state)).error, 'PROOF_INVALID');
});

test('signup atomically creates member/two consents/session and consumes proof', async () => {
  const state = await verified();
  const member = await signup(state);
  assert.equal(member.email, state.address);
  const consents = await query('select * from public.member_consents where member_id=$1', [member.id]);
  assert.equal(consents.length, 2);
  assert.deepEqual(consents.map(x => x.consent_type).sort(), ['privacy_collection','terms_of_service']);
  assert.ok(consents.every(x => x.version === 'dev-2026-10-02' && x.agreed_at));
  const session = (await query('select * from public.auth_sessions where member_id=$1', [member.id]))[0];
  assert.ok(Date.parse(session.expires_at) - Date.now() > 604790000);
  const verification = (await query('select * from public.email_verifications where id=$1', [state.id]))[0];
  assert.equal(verification.status, 'consumed'); assert.equal(verification.proof_digest,null);
  assert.equal((await signup(state, bytes('d'))).error, 'PROOF_INVALID');
  assert.equal((await rpc('begin_verification',[randomUUID(),state.address,code])).error,'EMAIL_EXISTS');
  const duplicate = await query('select count(*)::int as count from public.members where email=$1',[state.address]);
  assert.equal(duplicate[0].count,1);
});

test('stale terms do not consume proof; database failure rolls back all signup changes', async () => {
  const state = await verified();
  assert.equal((await signup(state, bytes('9'), 'old')).error,'CONSENT_VERSION_CHANGED');
  // Force a session PK collision after member and consent insertions.
  assert.equal((await signup(state)).error,'EMAIL_EXISTS');
  assert.equal((await query('select count(*)::int as count from public.members where email=$1',[state.address]))[0].count,0);
  assert.equal((await query('select status from public.email_verifications where id=$1',[state.id]))[0].status,'verified');
  assert.ok((await signup(state,bytes('9'))).id);
});

test('session renewal updates existing rows and does not restore deleted or expired sessions', async () => {
  const state = await verified(); const token=bytes('7'); const member=await signup(state,token);
  assert.equal((await query('select * from public.renew_auth_session($1)',[token]))[0].id,member.id);
  await query(`update public.auth_sessions set expires_at=clock_timestamp()-interval '1 second' where token_digest=$1`,[token]);
  assert.equal((await query('select * from public.renew_auth_session($1)',[token])).length,0);
  await query('delete from public.auth_sessions where token_digest=$1',[token]);
  assert.equal((await query('select * from public.renew_auth_session($1)',[token])).length,0);
});

test('anonymous and authenticated roles cannot access auth tables or RPCs', async () => {
  for (const role of ['anon','authenticated']) {
    await db.exec(`set role ${role}`);
    for (const table of ['members','member_consents','auth_sessions','email_verifications']) {
      await assert.rejects(db.query(`select * from public.${table}`),/permission denied/);
    }
    await assert.rejects(rpc('begin_verification',[randomUUID(),email(),code]),/permission denied/);
    await db.exec('reset role');
  }
  await db.exec('set role service_role');
  const state=await start(); assert.ok(state.id);
  await db.exec('reset role');
  await db.close();
});
