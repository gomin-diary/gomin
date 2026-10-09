import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { after, test } from 'node:test';

const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite');
const db = new PGlite();
after(() => db.close());
await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
  grant usage on schema public to service_role;
  create schema storage;
  create table storage.buckets(id text primary key,name text,public boolean,
    file_size_limit bigint,allowed_mime_types text[]);`);
const dir = new URL('../migrations/', import.meta.url);
for (const file of (await readdir(dir)).filter(name => name.endsWith('.sql')).sort()) await db.exec(await readFile(new URL(file, dir), 'utf8'));
const q = async (sql, args = []) => (await db.query(sql, args)).rows;
const rpc = async (fn, args) => (await q(`select public.${fn}(${args.map((_, i) => `$${i + 1}`).join(',')}) value`, args))[0].value;
const reject = (operation, message) => assert.rejects(operation, error => error.message.includes(message));
const output = { current_feeling: '긴장돼요.', main_concerns: ['시험', '진로'], emotion_tags: ['불안'] };
async function context() {
  const [member] = await q(`insert into members(email,name) values($1,'테스트') returning id`, [`${randomUUID()}@example.test`]);
  const [c] = await q('insert into conversations(member_id) values($1) returning *', [member.id]);
  return c;
}
const snapshot = c => rpc('gomin_talk_snapshot', [c.member_id, c.id]);
const send = (c, content = '공백 포함\n오늘 이야기', id = randomUUID()) => rpc('gomin_talk_send', [c.member_id, c.id, id, content]);
const summarize = (c, id = randomUUID()) => rpc('gomin_talk_start_summary', [c.member_id, c.id, id]);
const complete = (c, job, data, error = null) => rpc('gomin_talk_complete', [c.member_id, c.id, job.id, job.lease_token, data, error]);
const confirm = (c, summaryId) => rpc('gomin_talk_confirm', [c.member_id, c.id, summaryId]);

test('service-role commands persist acceptance before reply, limit waiting sends, and freeze summary only after reply settles', async () => {
  const c = await context();
  await db.exec('set role service_role');
  try {
    const accepted = await send(c);
    assert.equal(accepted.message.seq_no, 1);
    assert.equal(accepted.job.status, 'running');
    const before = await snapshot(c);
    assert.equal(before.messages.length, 1);
    assert.equal(before.messages[0].created_at, accepted.message.created_at);
    await reject(send(c), 'TALK_BUSY');
    await reject(summarize(c), 'TALK_BUSY');
    await complete(c, accepted.job, { content: '시험과 진로 때문에 긴장됐구나.' });
    const summaryJob = await summarize(c);
    assert.equal(summaryJob.job.source_until_seq_no, 2);
    await reject(send(c), 'TALK_BUSY');
    await complete(c, summaryJob.job, output);
    const after = await snapshot(c);
    assert.deepEqual(after.messages.map(m => m.seq_no), [1, 2]);
    assert.equal(after.phase, 'reviewing');
    const s = after.summaries[0];
    assert.equal(s.version, 1);
    assert.equal(s.source_until_seq_no, 2);
    const confirmed = await confirm(c, s.id);
    assert.ok(confirmed.confirmed_at);
    assert.equal((await confirm(c, s.id)).confirmed_at, confirmed.confirmed_at);
    assert.equal((await q('select count(*)::int n from diary_results'))[0].n, 0);
    assert.equal((await q(`select count(*)::int n from generation_jobs where kind='image'`))[0].n, 0);
    assert.equal((await q('select count(*)::int n from collection_entries'))[0].n, 0);
  } finally { await db.exec('reset role'); }
});

test('validates blank, 100 and 101 code points including whitespace, newlines and astral characters', async () => {
  for (const content of ['', ' \n\t', '가'.repeat(101)]) await reject(send(await context(), content), 'TALK_INVALID_INPUT');
  for (const content of ['가'.repeat(98) + ' \n', '🌱'.repeat(100)]) {
    const accepted = await send(await context(), content);
    assert.equal(accepted.message.content, content);
  }
});

test('reuses existing identifiers without restarting a failed job and rejects conflicting request bodies', async () => {
  const c = await context(), requestId = randomUUID();
  const first = await send(c, '원문', requestId);
  await complete(c, first.job, null, 'AI_FAILED');
  const repeated = await send(c, '원문', requestId);
  assert.equal(repeated.execute, false);
  assert.equal(repeated.job.id, first.job.id);
  assert.equal(repeated.job.status, 'failed');
  await reject(send(c, '다른 원문', requestId), 'TALK_CONFLICT');
  const summaryId = randomUUID(), summary = await summarize(c, summaryId);
  await complete(c, summary.job, null, 'AI_FAILED');
  assert.equal((await summarize(c, summaryId)).execute, false);
  assert.equal((await snapshot(c)).summaries.length, 0);
});

test('enforces ownership in reads, sends, summaries, confirmation, resume and completions', async () => {
  const c = await context(), other = await context();
  const accepted = await send(c);
  await complete(c, accepted.job, { content: '응답' });
  const job = await summarize(c);
  await complete(c, job.job, output);
  const s = (await snapshot(c)).summaries[0];
  const wrong = { ...c, member_id: other.member_id };
  for (const operation of [() => snapshot(wrong), () => send(wrong), () => summarize(wrong),
    () => confirm(wrong, s.id), () => rpc('gomin_talk_resume', [wrong.member_id, c.id]),
    () => complete(wrong, accepted.job, { content: 'forged' })]) await reject(operation(), 'TALK_NOT_FOUND');
  await reject(confirm(other, s.id), 'TALK_NOT_FOUND');
  assert.equal((await snapshot(c)).messages.length, 2);
});

test('same-conversation resume appends original messages and creates a new immutable summary version', async () => {
  const c = await context();
  const first = await send(c);
  await complete(c, first.job, { content: '첫 응답' });
  const j1 = await summarize(c); await complete(c, j1.job, output);
  const before = await snapshot(c), s1 = before.summaries[0];
  await rpc('gomin_talk_resume', [c.member_id, c.id]);
  const additional = await send(c, '추가 진로 고민'); await complete(c, additional.job, { content: '추가 응답' });
  await reject(confirm(c, s1.id), 'TALK_STALE_SUMMARY');
  const j2 = await summarize(c); await complete(c, j2.job, { ...output, main_concerns: ['시험', '추가 진로 고민'] });
  const after = await snapshot(c);
  assert.deepEqual(after.messages.slice(0, 2), before.messages);
  assert.deepEqual(after.messages.map(m => m.seq_no), [1, 2, 3, 4]);
  assert.deepEqual(after.summaries.map(s => s.version), [1, 2]);
  assert.notEqual(after.summaries[1].id, s1.id);
  assert.equal(after.summaries[1].source_until_seq_no, 4);
  await reject(confirm(c, s1.id), 'TALK_STALE_SUMMARY');
  await confirm(c, after.summaries[1].id);
});

test('bounded execution marks timeout without retry and discards stale lease completions', async () => {
  const c = await context(), accepted = await send(c);
  await q(`update generation_jobs set lease_expires_at=clock_timestamp()-interval '1 second' where id=$1`, [accepted.job.id]);
  const read = await snapshot(c);
  assert.equal(read.jobs[0].status, 'failed');
  assert.equal(read.jobs[0].error_code, 'AI_TIMEOUT');
  assert.equal(await complete(c, accepted.job, { content: 'late answer' }), false);
  assert.equal((await snapshot(c)).messages.length, 1);
  assert.equal((await q('select attempt_count from generation_jobs where id=$1', [accepted.job.id]))[0].attempt_count, 1);
});

test('failure leaves no completed summary and source boundary uses only the requested conversation', async () => {
  const c = await context(), other = await context();
  const accepted = await send(c); await complete(c, accepted.job, null, 'AI_FAILED');
  await send(other, '별도 대화');
  const summary = await summarize(c);
  assert.equal(summary.job.source_until_seq_no, 1);
  await complete(c, summary.job, null, 'AI_NOT_CONFIGURED');
  const data = await snapshot(c);
  assert.equal(data.summaries.length, 0);
  assert.equal(data.messages[0].content, accepted.message.content);
  assert.equal(data.jobs.at(-1).status, 'failed');
});

test('anon and authenticated cannot call any privileged conversation command', async () => {
  const c = await context();
  for (const role of ['anon', 'authenticated']) {
    await db.exec(`set role ${role}`);
    try {
      for (const operation of [() => snapshot(c), () => send(c), () => summarize(c),
        () => confirm(c, randomUUID()), () => rpc('gomin_talk_resume', [c.member_id, c.id]),
        () => rpc('gomin_talk_lock', [c.member_id, c.id]),
        () => complete(c, { id: randomUUID(), lease_token: randomUUID() }, null, 'AI_FAILED')]) {
        await assert.rejects(operation(), error => error.code === '42501');
      }
    }
    finally { await db.exec('reset role'); }
  }
});
