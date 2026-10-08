import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { after, test } from 'node:test';

// Disposable PostgreSQL only; never loads application environment files.
const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite');
const db = new PGlite();
after(() => db.close());
await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
  grant usage on schema public to service_role;`);
// PGlite has no Supabase Storage service. Model only the migration's bucket metadata.
await db.exec(`create schema storage;
  create table storage.buckets(id text primary key, name text, public boolean,
    file_size_limit bigint, allowed_mime_types text[]);`);
const migrationDir = new URL('../migrations/', import.meta.url);
for (const file of (await readdir(migrationDir)).filter(name => name.endsWith('.sql')).sort()) {
  await db.exec(await readFile(new URL(file, migrationDir), 'utf8'));
}
const tables = ['conversations', 'conversation_messages', 'conversation_summaries',
  'generation_jobs', 'diary_results', 'collection_entries'];
const q = async (sql, args = []) => (await db.query(sql, args)).rows;
const rejectsCode = (operation, code) => assert.rejects(operation, error => error.code === code);

async function submit(c, s, key = randomUUID(), fingerprint = 'fingerprint', model = 'image-test') {
  return (await q(`select submit_diary_image($1,$2,$3,$4,$5,'text-test',$6,'1024x1024') as job`,
    [c.member_id, c.id, s.id, key, fingerprint, model]))[0].job;
}
async function claim(id) {
  return (await q('select claim_diary_image($1,600) as job', [id]))[0].job;
}
async function finalize(j, token = j.lease_token, title = '오늘의 기록') {
  return (await q("select finalize_diary_image($1,$2,$3,'잘하고 있어요','gomin-diary-images',$4) as result",
    [j.id, token, title, `${j.id}.png`]))[0].result;
}

async function conversation(memberId) {
  if (!memberId) {
    [memberId] = (await q(`insert into members(email,name) values($1,'테스트 회원') returning id`,
      [`${randomUUID()}@example.test`])).map(row => row.id);
  }
  const [row] = await q('insert into conversations(member_id) values($1) returning *', [memberId]);
  return row;
}
async function message(c, seq = 1) {
  const [row] = await q(`insert into conversation_messages
    (conversation_id,seq_no,role,content,client_message_id) values($1,$2,'user','오늘의 고민',$3) returning *`,
  [c.id, seq, randomUUID()]);
  return row;
}
async function job(c, { kind = 'summary', inputMessage = null, inputSummary = null,
  boundary = 1, requestKey = randomUUID() } = {}) {
  const [row] = await q(`insert into generation_jobs(member_id,conversation_id,kind,input_message_id,
    input_summary_id,source_until_seq_no,idempotency_key,request_fingerprint)
    values($1,$2,$3,$4,$5,$6,$7,'test-request-fingerprint') returning *`,
  [c.member_id, c.id, kind, inputMessage, inputSummary, boundary, requestKey]);
  return row;
}
async function finish(j, writeOutput) {
  return db.transaction(async tx => {
    await tx.query(`update generation_jobs set status='succeeded',finished_at=clock_timestamp(),
      lease_token=null,lease_expires_at=null where id=$1`, [j.id]);
    return writeOutput(tx);
  });
}
async function summary(c, { version = 1, confirmed = true } = {}) {
  const j = await job(c);
  const s = await finish(j, async tx => (await tx.query(`insert into conversation_summaries
    (member_id,conversation_id,version,source_until_seq_no,current_feeling,main_concerns,
     emotion_tags,generation_job_id) values($1,$2,$3,1,'불안해요',array['시험'],array['불안'],$4) returning *`,
  [c.member_id, c.id, version, j.id])).rows[0]);
  if (confirmed) await q('update conversation_summaries set confirmed_at=clock_timestamp() where id=$1', [s.id]);
  return s;
}
async function result(c, s, completedAt = '2026-10-07T15:30:00Z') {
  const j = await job(c, { kind: 'image', inputSummary: s.id, boundary: null });
  return finish(j, async tx => (await tx.query(`insert into diary_results
    (member_id,summary_id,generation_job_id,title,encouragement_text,image_bucket,image_object_key,completed_at)
    values($1,$2,$3,'오늘의 기록','잘 해내고 있어요','private-diaries',$4,$5) returning *`,
  [c.member_id, s.id, j.id, `${j.id}.png`, completedAt])).rows[0]);
}
async function context() {
  const c = await conversation();
  const m = await message(c);
  return { c, m };
}

test('adds six private business tables after the existing authentication migrations', async () => {
  const rows = await q(`select relname,relrowsecurity from pg_class
    where relnamespace='public'::regnamespace and relname=any($1::text[]) order by relname`, [tables]);
  assert.equal(rows.length, 6);
  assert.ok(rows.every(row => row.relrowsecurity));
});

test('atomic image submission confirms once, deduplicates and rejects changed or stale inputs', async () => {
  const { c } = await context();
  const s = await summary(c, { confirmed: false });
  const key = randomUUID();
  const first = await submit(c, s, key);
  const confirmed = (await q('select confirmed_at from conversation_summaries where id=$1', [s.id]))[0];
  assert.equal((await submit(c, s, key)).id, first.id);
  assert.deepEqual((await q('select confirmed_at from conversation_summaries where id=$1', [s.id]))[0], confirmed);
  await rejectsCode(submit(c, s, key, 'changed'), 'P0001');
  const other = await conversation();
  await rejectsCode(submit(other, s), 'P0002');
  await message(c, 2);
  await rejectsCode(submit(c, s), 'P0001');
  assert.equal((await submit(c, s, key)).id, first.id); // replay survives later summary changes
});

test('invalid options roll back confirmation and job creation, and RPC is server-only', async () => {
  const { c } = await context();
  const s = await summary(c, { confirmed: false });
  await rejectsCode(submit(c, s, randomUUID(), 'fingerprint', ''), '23514');
  assert.equal((await q('select confirmed_at from conversation_summaries where id=$1', [s.id]))[0].confirmed_at, null);
  assert.equal((await q("select count(*)::int n from generation_jobs where input_summary_id=$1", [s.id]))[0].n, 0);
  assert.equal((await q("select has_function_privilege('anon','submit_diary_image(uuid,uuid,uuid,uuid,text,text,text,text)','EXECUTE') ok"))[0].ok, false);
  assert.equal((await q("select has_function_privilege('service_role','submit_diary_image(uuid,uuid,uuid,uuid,text,text,text,text)','EXECUTE') ok"))[0].ok, true);
  await db.exec('set role service_role');
  try { assert.equal((await submit(c, s)).status, 'queued'); }
  finally { await db.exec('reset role'); }
});

test('claims one execution token, expiry fails without automatically retrying the provider', async () => {
  const { c } = await context();
  const s = await summary(c);
  const j = await submit(c, s);
  const running = await claim(j.id);
  assert.equal(running.status, 'running');
  assert.equal(running.attempt_count, 1);
  assert.equal(running.options.image_model, 'image-test');
  assert.ok(running.lease_token);
  assert.equal(await claim(j.id), null);
  await q("update generation_jobs set lease_expires_at=clock_timestamp()-interval '1 second' where id=$1", [j.id]);
  await q('select expire_diary_image_leases()');
  const [failed] = await q('select * from generation_jobs where id=$1', [j.id]);
  assert.equal(failed.status, 'failed');
  assert.equal(failed.error_code, 'LEASE_EXPIRED');
  assert.equal(failed.lease_token, null);
  assert.equal(await claim(j.id), null);
  assert.equal((await submit(c, s, j.idempotency_key)).status, 'failed');
});

test('rejects duplicate message submissions and duplicate sequence numbers', async () => {
  const { c, m } = await context();
  await rejectsCode(q(`insert into conversation_messages
    (conversation_id,seq_no,role,content,client_message_id) values($1,2,'user','再送',$2)`,
  [c.id, m.client_message_id]), '23505');
  await rejectsCode(message(c, 1), '23505');
  const [stored] = await q('select count(*)::int n from conversation_messages where conversation_id=$1', [c.id]);
  assert.equal(stored.n, 1);
});

test('finalization is atomic, rejects stale tokens and preserves first result on replay', async () => {
  const { c } = await context();
  const s = await summary(c);
  const j = await claim((await submit(c, s)).id);
  await rejectsCode(finalize(j, randomUUID()), 'P0001');
  await rejectsCode(finalize(j, j.lease_token, '   '), '23514');
  assert.equal((await q('select status from generation_jobs where id=$1', [j.id]))[0].status, 'running');
  assert.equal((await q('select count(*)::int n from diary_results where generation_job_id=$1', [j.id]))[0].n, 0);
  const result = await finalize(j);
  assert.deepEqual(await finalize(j, j.lease_token, '변경될 수 없어요'), result);
  const [job] = await q('select status,finished_at,lease_token from generation_jobs where id=$1', [j.id]);
  assert.equal(job.status, 'succeeded');
  assert.equal(job.lease_token, null);
  assert.equal(job.finished_at.toISOString(), new Date(result.completed_at).toISOString());
  assert.equal((await q('select phase from conversations where id=$1', [c.id]))[0].phase, 'ready');
});

test('explicit retry preserves inputs and identity, and replaced tokens cannot write', async () => {
  const { c } = await context();
  const s = await summary(c);
  const j = await claim((await submit(c, s)).id);
  const fail = async token => (await q("select fail_diary_image($1,$2,'TIMEOUT') ok", [j.id, token]))[0].ok;
  assert.equal(await fail(randomUUID()), false);
  assert.equal(await fail(j.lease_token), true);
  await rejectsCode(q('select retry_diary_image($1,$2)', [randomUUID(), j.id]), 'P0002');
  const retry = (await q('select retry_diary_image($1,$2) job', [c.member_id, j.id]))[0].job;
  assert.equal(retry.id, j.id);
  assert.equal(retry.idempotency_key, j.idempotency_key);
  assert.equal(retry.request_fingerprint, j.request_fingerprint);
  assert.equal(retry.input_summary_id, s.id);
  const next = await claim(j.id);
  assert.equal(next.attempt_count, 2);
  assert.notEqual(next.lease_token, j.lease_token);
  assert.equal(await fail(j.lease_token), false);
  await rejectsCode(finalize(j), 'P0001');
  assert.ok(await finalize(next));
});

test('expired completion cannot create a result and other active jobs keep generating phase', async () => {
  const { c } = await context();
  const s = await summary(c);
  const first = await claim((await submit(c, s)).id);
  const second = await claim((await submit(c, s)).id);
  await finalize(first);
  assert.equal((await q('select phase from conversations where id=$1', [c.id]))[0].phase, 'generating');
  await q("update generation_jobs set lease_expires_at=clock_timestamp()-interval '1 second' where id=$1", [second.id]);
  await rejectsCode(finalize(second), 'P0001');
});

test('requires the correct ID shape for each message role and rejects blank content', async () => {
  const { c } = await context();
  await rejectsCode(q(`insert into conversation_messages
    (conversation_id,seq_no,role,content) values($1,2,'user','내용')`, [c.id]), '23514');
  await rejectsCode(q(`insert into conversation_messages
    (conversation_id,seq_no,role,content) values($1,2,'assistant','내용')`, [c.id]), '23514');
  await rejectsCode(q(`insert into conversation_messages
    (conversation_id,seq_no,role,content,client_message_id) values($1,2,'user',E' \n\t',$2)`,
  [c.id, randomUUID()]), '23514');
});

test('allows multiple queued jobs in one conversation while deduplicating each request key', async () => {
  const { c } = await context();
  const first = await job(c);
  await job(c);
  await rejectsCode(job(c, { requestKey: first.idempotency_key }), '23505');
  assert.equal((await q('select count(*)::int n from generation_jobs where conversation_id=$1', [c.id]))[0].n, 2);
});

test('a reply job must target a user message in the same conversation and can produce only one reply', async () => {
  const { c, m } = await context();
  const j = await job(c, { kind: 'reply', inputMessage: m.id });
  const answer = await finish(j, async tx => (await tx.query(`insert into conversation_messages
    (conversation_id,seq_no,role,content,generation_job_id) values($1,2,'assistant','이야기해 주세요',$2) returning *`,
  [c.id, j.id])).rows[0]);
  await rejectsCode(job(c, { kind: 'reply', inputMessage: m.id }), '23505');
  await rejectsCode(job(c, { kind: 'reply', inputMessage: answer.id, boundary: 2 }), '23514');
  await rejectsCode(q(`insert into conversation_messages
    (conversation_id,seq_no,role,content,generation_job_id) values($1,3,'assistant','중복 답변',$2)`,
  [c.id, j.id]), '23505');
  const unclaimed = await message(c, 3);
  const other = await conversation(c.member_id);
  await message(other, 3);
  await rejectsCode(job(other, { kind: 'reply', inputMessage: unclaimed.id, boundary: 3 }), '23503');
});

test('rejects cross-member ownership and cross-conversation summary inputs', async () => {
  const { c } = await context();
  const other = await conversation();
  await message(other);
  await rejectsCode(q(`insert into generation_jobs
    (member_id,conversation_id,kind,source_until_seq_no,idempotency_key,request_fingerprint)
    values($1,$2,'summary',1,$3,'fingerprint')`, [c.member_id, other.id, randomUUID()]), '23503');
  const s = await summary(c);
  const sameOwnerOther = await conversation(c.member_id);
  await message(sameOwnerOther);
  await rejectsCode(job(sameOwnerOther, { kind: 'image', inputSummary: s.id, boundary: null }), '23503');
});

test('image jobs require confirmed summaries; stale summaries cannot be confirmed', async () => {
  const { c } = await context();
  const s = await summary(c, { confirmed: false });
  await rejectsCode(job(c, { kind: 'image', inputSummary: s.id, boundary: null }), '23514');
  await message(c, 2);
  await rejectsCode(q('update conversation_summaries set confirmed_at=clock_timestamp() where id=$1', [s.id]), '23514');
});

test('summary content is immutable and its confirmation cannot be cleared', async () => {
  const { c } = await context();
  const s = await summary(c);
  await rejectsCode(q(`update conversation_summaries set current_feeling='바꾼 내용' where id=$1`, [s.id]), '23514');
  await rejectsCode(q('update conversation_summaries set confirmed_at=null where id=$1', [s.id]), '23514');
  const version2 = await summary(c, { version: 2 });
  assert.notEqual(s.id, version2.id);
});

test('successful jobs and their output must commit together', async () => {
  const { c, m } = await context();
  const j = await job(c, { kind: 'reply', inputMessage: m.id });
  await rejectsCode(q(`update generation_jobs set status='succeeded',finished_at=clock_timestamp() where id=$1`,
    [j.id]), '23514');
  await rejectsCode(q(`insert into conversation_messages
    (conversation_id,seq_no,role,content,generation_job_id) values($1,2,'assistant','未完成',$2)`,
  [c.id, j.id]), '23514');
  assert.equal((await q('select status from generation_jobs where id=$1', [j.id]))[0].status, 'queued');
  assert.equal((await q('select count(*)::int n from conversation_messages where conversation_id=$1', [c.id]))[0].n, 1);
});

test('derives diary_date in Korea across UTC midnight regardless of the database session timezone', async () => {
  const { c } = await context();
  const s = await summary(c);
  await db.exec(`set time zone 'Pacific/Honolulu'`);
  try {
    const before = await result(c, s, '2026-10-07T14:59:59Z');
    const afterMidnight = await result(c, s, '2026-10-07T15:00:00Z');
    const dates = await q('select diary_date::text as date_text from diary_results where id=any($1::uuid[]) order by completed_at',
      [[before.id, afterMidnight.id]]);
    assert.deepEqual(dates.map(row => row.date_text), ['2026-10-07', '2026-10-08']);
    await rejectsCode(q(`update diary_results set completed_at='2026-10-09T00:00:00Z' where id=$1`,
      [before.id]), '23514');
  } finally {
    await db.exec(`set time zone 'UTC'`);
  }
});

test('rejects results whose summary differs from the image job input', async () => {
  const { c } = await context();
  const s1 = await summary(c);
  const s2 = await summary(c, { version: 2 });
  const j = await job(c, { kind: 'image', inputSummary: s1.id, boundary: null });
  await rejectsCode(finish(j, tx => tx.query(`insert into diary_results
    (member_id,summary_id,generation_job_id,title,encouragement_text,image_bucket,image_object_key)
    values($1,$2,$3,'제목','위로','private-diaries',$4)`,
  [c.member_id, s2.id, j.id, `${j.id}.png`])), '23503');
});

test('retains unsaved and regenerated results and deduplicates collection entries', async () => {
  const { c } = await context();
  const s = await summary(c);
  const r1 = await result(c, s, '2020-01-01T00:00:00Z');
  const r2 = await result(c, s);
  assert.equal((await q('select count(*)::int n from diary_results where summary_id=$1', [s.id]))[0].n, 2);
  assert.equal((await q('select count(*)::int n from collection_entries where member_id=$1', [c.member_id]))[0].n, 0);
  const [entry] = await q(`insert into collection_entries(member_id,source_result_id)
    values($1,$2) returning *`, [c.member_id, r1.id]);
  await rejectsCode(q('insert into collection_entries(member_id,source_result_id) values($1,$2)',
    [c.member_id, r1.id]), '23505');
  const other = await conversation();
  await rejectsCode(q('insert into collection_entries(member_id,source_result_id) values($1,$2)',
    [other.member_id, r2.id]), '23503');
  assert.equal((await q('select saved_at from collection_entries where id=$1', [entry.id]))[0].saved_at.getTime(),
    entry.saved_at.getTime());
});

test('job inputs cannot change on retry, and failed jobs can queue again without changing identity', async () => {
  const { c } = await context();
  const j = await job(c);
  await q(`update generation_jobs set status='failed',error_code='AI_FAILED',finished_at=clock_timestamp() where id=$1`,
    [j.id]);
  await rejectsCode(q(`update generation_jobs set request_fingerprint='changed' where id=$1`, [j.id]), '23514');
  await q(`update generation_jobs set status='queued',error_code=null,finished_at=null where id=$1`, [j.id]);
  assert.equal((await q('select status from generation_jobs where id=$1', [j.id]))[0].status, 'queued');
});

test('anonymous clients cannot access tables; the service role can write but cannot delete records', async () => {
  const { c } = await context();
  for (const role of ['anon', 'authenticated']) {
    await db.exec(`set role ${role}`);
    try {
      for (const table of tables) await rejectsCode(db.query(`select * from public.${table}`), '42501');
    } finally {
      await db.exec('reset role');
    }
  }
  await db.exec('set role service_role');
  try {
    await message(c, 2);
    for (const table of tables) {
      assert.equal((await q(`select has_table_privilege(current_user,$1,'DELETE') allowed`, [table]))[0].allowed, false);
    }
    await rejectsCode(q('delete from conversations where id=$1', [c.id]), '42501');
  } finally {
    await db.exec('reset role');
  }
  await rejectsCode(q('delete from members where id=$1', [c.member_id]), '23001');
});

test('the service role can complete the summary-to-collection flow with only the granted privileges', async () => {
  const { c } = await context();
  await db.exec('set role service_role');
  try {
    const s = await summary(c);
    const r = await result(c, s);
    const [entry] = await q(`insert into collection_entries(member_id,source_result_id)
      values($1,$2) returning *`, [c.member_id, r.id]);
    assert.equal(entry.source_result_id, r.id);
    await rejectsCode(q(`update conversation_summaries set current_feeling='바꾼 내용' where id=$1`, [s.id]), '42501');
    await rejectsCode(q(`update diary_results set title='바꾼 제목' where id=$1`, [r.id]), '42501');
  } finally {
    await db.exec('reset role');
  }
});
