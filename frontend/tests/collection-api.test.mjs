import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createApiCollectionRepository, CollectionNotFoundError } from '../src/lib/collection.ts';

const row = id => ({ id, source_result_id: '00000000-0000-4000-8000-000000000001', diary_date: '2026-10-08',
  title: '나의 기록', emotion_tags: ['불안', '기쁨', '기대'] });
const id = '00000000-0000-4000-8000-000000000002';

test('real repository maps original DB fields, walks cursors and never sends member IDs', async () => {
  const calls = [];
  const repo = createApiCollectionRepository(async path => {
    calls.push(path);
    if (path.startsWith('/api/v1/collection?')) return { items: [row(id)], next_cursor: calls.length === 1 ? 'cursor' : null };
    return { ...row(id), encouragement_text: '힘내요', current_feeling: '불안해요', main_concerns: ['시험', '관계'] };
  });
  const items = await repo.list('should-not-be-sent');
  assert.equal(items.length, 2);
  assert.deepEqual(items[0].categories, ['기쁨', '불안']);
  assert.equal(items[0].image.accessPath, `/api/v1/collection/${id}/image-url`);
  assert.ok(calls[1].includes('cursor=cursor'));
  assert.ok(calls.every(path => !path.includes('should-not-be-sent')));
  const detail = await repo.detail('should-not-be-sent', id);
  assert.deepEqual(detail.concerns, ['시험', '관계']);
  assert.equal(detail.caption, '힘내요');
  assert.equal(detail.date, '2026-10-08');
});

test('server category filter, abort, not-found and unavailable errors stay distinct', async () => {
  const abort = new AbortController();
  const repo = createApiCollectionRepository(async (path, init) => {
    assert.equal(init.signal, abort.signal);
    assert.equal(new URL(path, 'https://example.test').searchParams.get('emotion'), '슬픔');
    return { items: [], next_cursor: null };
  });
  assert.deepEqual(await repo.page(null, '슬픔', abort.signal), { items: [], nextCursor: null });
  const missing = createApiCollectionRepository(async () => { throw { status: 404 }; });
  await assert.rejects(missing.detail('owner', id), CollectionNotFoundError);
  const failure = new Error('unavailable');
  const unavailable = createApiCollectionRepository(async () => { throw failure; });
  await assert.rejects(unavailable.detail('owner', id), error => error === failure);
  abort.abort();
  await assert.rejects(repo.list('owner', abort.signal), error => error.name === 'AbortError');
});
