import assert from 'node:assert/strict';
import { test } from 'node:test';
import { canFinish, canSend, createTalkController, enterSends, messageLength, validMessage } from '../src/lib/talk.ts';

const delay = () => new Promise(resolve => setTimeout(resolve, 3));
const until = async predicate => { for (let i = 0; i < 150; i++) { if (predicate()) return; await delay(); } throw new Error('Timed out'); };
function fixture() {
  let conversation = { id: 'conversation-a', phase: 'chatting', messages: [], summaries: [], jobs: [] };
  let creates = 0, sends = 0, summaries = 0;
  const snapshot = () => structuredClone(conversation);
  const api = {
    async create() { creates++; return snapshot(); },
    async read() { return snapshot(); },
    async send(id, content) {
      sends++;
      const message = { id: `message-${sends}`, conversation_id: id, seq_no: conversation.messages.length + 1, role: 'user', content, created_at: '2026-10-08T05:00:00Z' };
      const job = { id: `reply-${sends}`, kind: 'reply', status: 'running', source_until_seq_no: message.seq_no, error_code: null };
      conversation.messages.push(message); conversation.jobs.push(job);
      return structuredClone({ message, job });
    },
    async summarize() {
      summaries++; conversation.phase = 'summarizing';
      const job = { id: `summary-${summaries}`, kind: 'summary', status: 'running', source_until_seq_no: conversation.messages.length, error_code: null };
      conversation.jobs.push(job); return structuredClone(job);
    },
    async resume() { conversation.phase = 'chatting'; return snapshot(); },
    async confirm(id, summaryId) {
      const summary = conversation.summaries.find(s => s.id === summaryId);
      summary.confirmed_at = '2026-10-08T05:10:00Z';
      return { conversation_id: id, summary_id: summaryId, version: summary.version, confirmed: true, summary: structuredClone(summary), next_stage: 'image_generation', next_stage_status: 'not_started' };
    },
  };
  function reply(error = null) {
    const job = conversation.jobs.filter(j => j.kind === 'reply').at(-1);
    job.status = error ? 'failed' : 'succeeded'; job.error_code = error;
    if (!error) conversation.messages.push({ id: `answer-${sends}`, conversation_id: conversation.id, seq_no: conversation.messages.length + 1, role: 'assistant', content: '이전 이야기를 이어가는 응답', created_at: '2026-10-08T05:01:00Z' });
  }
  function summary(error = null) {
    const job = conversation.jobs.filter(j => j.kind === 'summary').at(-1);
    job.status = error ? 'failed' : 'succeeded'; job.error_code = error;
    if (!error) { conversation.phase = 'reviewing'; conversation.summaries.push({ id: `summary-output-${summaries}`, conversation_id: conversation.id, version: summaries, source_until_seq_no: job.source_until_seq_no, current_feeling: '불안해요', main_concerns: conversation.messages.filter(m => m.role === 'user').map(m => m.content), emotion_tags: ['불안'], confirmed_at: null, created_at: '2026-10-08T05:02:00Z' }); }
  }
  return { api, reply, summary, snapshot, calls: () => ({ creates, sends, summaries }), controller: createTalkController(api, { pollMs: 1 }) };
}

test('counts code points with spaces/newlines and rejects blank and 101-character input', () => {
  for (const content of ['', ' ', '\n\t', '가'.repeat(101)]) assert.equal(validMessage(content), false);
  assert.equal(validMessage('가'.repeat(98) + ' \n'), true);
  assert.equal(messageLength('🌱'.repeat(100)), 100);
  assert.equal(validMessage('🌱'.repeat(100)), true);
});
test('PC, mobile, Shift and Korean IME have distinct Enter behavior', () => {
  assert.equal(enterSends({ mobile: false, shift: false, composing: false }), true);
  for (const properties of [{ mobile: true }, { shift: true }, { composing: true }, { keyCode: 229 }]) assert.equal(enterSends({ mobile: false, shift: false, composing: false, ...properties }), false);
});
test('persistence activates finish before reply; normal waiting preserves new edits and never sends them automatically', async () => {
  const f = fixture(), c = f.controller;
  assert.equal(canFinish(c.getSnapshot()), false);
  c.setDraft('저장할 원문'); const send = c.send();
  await until(() => c.getSnapshot().replyPending);
  assert.equal(canFinish(c.getSnapshot()), true);
  c.setDraft('기다리며 수정한 초안');
  assert.equal(canSend(c.getSnapshot()), false); await c.send();
  f.reply(); await send;
  assert.equal(c.getSnapshot().draft, '기다리며 수정한 초안');
  assert.deepEqual(f.calls(), { creates: 1, sends: 1, summaries: 0 });
  assert.equal(canSend(c.getSnapshot()), true); c.dispose();
});

test('an already saved conversation can finish during acceptance of another message, before freezing its source', async () => {
  const f = fixture(), c = f.controller;
  c.setDraft('첫 고민'); const first = c.send(); await until(() => c.getSnapshot().replyPending); f.reply(); await first;
  const originalSend = f.api.send; let accept;
  f.api.send = (...args) => new Promise(resolve => { accept = () => resolve(originalSend(...args)); });
  c.setDraft('추가 고민'); const second = c.send();
  assert.equal(canFinish(c.getSnapshot()), true);
  const finish = c.finish(); assert.equal(c.getSnapshot().view, 'wrapup'); assert.equal(f.calls().summaries, 0);
  accept(); await until(() => c.getSnapshot().replyPending); assert.equal(f.calls().summaries, 0);
  f.reply(); await second; await until(() => f.calls().summaries === 1);
  assert.equal(c.getSnapshot().conversation.jobs.at(-1).source_until_seq_no, 4);
  f.summary(); await finish; c.dispose();
});
test('finish while waiting moves immediately, waits for reply, excludes draft, then supports same-ID resummary and exact handoff', async () => {
  const f = fixture(), c = f.controller;
  c.setDraft('첫 고민'); const send = c.send(); await until(() => c.getSnapshot().replyPending);
  c.setDraft('전송하지 않은 초안'); const finish = c.finish();
  assert.equal(c.getSnapshot().view, 'wrapup'); assert.equal(c.getSnapshot().summaryStatus, 'waiting');
  assert.equal(f.calls().summaries, 0); f.reply(); await send;
  await until(() => f.calls().summaries === 1); f.summary(); await finish;
  assert.equal(c.getSnapshot().view, 'summary'); assert.equal(c.getSnapshot().draft, '전송하지 않은 초안');
  assert.deepEqual(c.getSnapshot().conversation.summaries[0].main_concerns, ['첫 고민']);
  await c.resume(); assert.equal(c.getSnapshot().conversation.id, 'conversation-a');
  c.setDraft('추가 고민'); const additional = c.send(); await until(() => c.getSnapshot().replyPending); f.reply(); await additional;
  const resummary = c.finish(); await until(() => f.calls().summaries === 2); f.summary(); await resummary;
  await c.confirm(); const handoff = c.getSnapshot().handoff;
  assert.equal(handoff.version, 2); assert.equal(handoff.summary_id, 'summary-output-2');
  assert.deepEqual(handoff.summary.main_concerns, ['첫 고민', '추가 고민']);
  assert.equal(handoff.next_stage_status, 'not_started'); c.dispose();
});
test('reopen restores saved order and time, and has no draft storage', async () => {
  const f = fixture(), c = f.controller; c.setDraft('첫 원문'); const send = c.send(); await until(() => c.getSnapshot().replyPending); f.reply(); await send;
  c.setDraft('자동저장하면 안 되는 초안'); c.dispose();
  const reopened = createTalkController(f.api, { pollMs: 1 }); await reopened.load('conversation-a');
  assert.deepEqual(reopened.getSnapshot().conversation.messages, f.snapshot().messages);
  assert.equal(reopened.getSnapshot().draft, ''); reopened.dispose();
});
test('reply and summary failures remain failures without fallback, retry or old-summary success', async () => {
  const f = fixture(), c = f.controller; c.setDraft('실패 검증'); const send = c.send(); await until(() => c.getSnapshot().replyPending); f.reply('AI_NOT_CONFIGURED'); await send;
  assert.match(c.getSnapshot().replyError, /아직 연결/); assert.equal(c.getSnapshot().conversation.messages.length, 1);
  const finish = c.finish(); await until(() => f.calls().summaries === 1); f.summary('AI_FAILED'); await finish;
  assert.equal(c.getSnapshot().summaryStatus, 'error'); assert.equal(c.getSnapshot().view, 'wrapup');
  assert.equal(c.getSnapshot().handoff, null); await c.confirm(); assert.equal(c.getSnapshot().view, 'wrapup');
  assert.equal(f.calls().summaries, 1); c.dispose();
});
test('transport and confirm failures stop without retry or false confirmation', async () => {
  const f = fixture(); f.api.read = async () => { throw new Error('offline'); };
  const c = f.controller; c.setDraft('전송'); const send = c.send(); await send;
  assert.match(c.getSnapshot().replyError, /상태를 확인/); assert.equal(f.calls().sends, 1); c.dispose();
  const g = fixture(), d = g.controller; d.setDraft('원문'); const request = d.send(); await until(() => d.getSnapshot().replyPending); g.reply(); await request;
  const finish = d.finish(); await until(() => g.calls().summaries === 1); g.summary(); await finish;
  g.api.confirm = async () => { throw new Error('not authorized'); }; await d.confirm();
  assert.equal(d.getSnapshot().handoff, null); assert.equal(d.getSnapshot().view, 'summary'); assert.ok(d.getSnapshot().confirmError); d.dispose();
});
test('disposal and development effect replay ignore stale account data', async () => {
  const f = fixture(); let resolve; const pending = new Promise(yes => { resolve = yes; });
  f.api.read = () => pending; const c = f.controller; const loading = c.load('conversation-a'); c.dispose();
  const before = c.getSnapshot(); resolve(f.snapshot()); await loading; assert.equal(c.getSnapshot(), before);
  c.activate(); f.api.read = async () => f.snapshot(); await c.load('conversation-a'); assert.equal(c.getSnapshot().status, 'ready'); c.dispose();
});
