import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { registerHooks } from 'node:module';

process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.example.test';
// Match Next.js extensionless imports while running the real TS modules in Node.
const hooks = registerHooks({ resolve(specifier, context, nextResolve) {
  return nextResolve(specifier === './api' && context.parentURL.endsWith('/storage.ts')
    ? './api.ts' : specifier, context);
} });
const { uploadFile } = await import('../src/lib/storage.ts');
hooks.deregister();
const originalFetch = globalThis.fetch;
after(() => { globalThis.fetch = originalFetch; });

const path = '12345678-1234-5678-1234-567812345678/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const uploadUrl = `https://example.supabase.co/storage/v1/object/upload/sign/gomin-files/${path}?token=test-token`;
const grant = { bucket: 'gomin-files', path, upload_url: uploadUrl, expires_in: 7200, max_file_size_bytes: 10485760 };
const file = () => new File(['hello'], '고민.txt', { type: 'text/plain' });
const success = (data = grant) => Response.json({ success: true, data, error: null });

test('mint with session then PUT binary without cookies and return only after success', async () => {
  const source = file();
  const controller = new AbortController();
  let calls = 0;
  globalThis.fetch = async (url, init) => {
    calls++;
    assert.equal(init.signal, controller.signal);
    if (calls === 1) {
      assert.equal(url, 'https://api.example.test/api/v1/files/upload-url');
      assert.equal(init.method, 'POST');
      assert.equal(init.credentials, 'include');
      assert.deepEqual(JSON.parse(init.body), { filename: '고민.txt', size: 5, content_type: 'text/plain' });
      return success();
    }
    assert.equal(url, uploadUrl);
    assert.equal(init.method, 'PUT');
    assert.equal(init.body, source);
    assert.equal(init.credentials, 'omit');
    assert.equal(init.referrerPolicy, 'no-referrer');
    assert.equal(init.cache, 'no-store');
    assert.equal(new Headers(init.headers).get('Content-Type'), 'text/plain');
    assert.equal(new Headers(init.headers).get('Authorization'), null);
    assert.equal(new Headers(init.headers).get('x-upsert'), null);
    return Response.json({ Key: `gomin-files/${path}` });
  };
  assert.deepEqual(await uploadFile(source, { signal: controller.signal }), {
    bucket: 'gomin-files', path, filename: '고민.txt', size: 5, content_type: 'text/plain',
  });
  assert.equal(calls, 2);
});

test('missing browser MIME uses application/octet-stream in both requests', async () => {
  let calls = 0;
  globalThis.fetch = async (_url, init) => {
    if (++calls === 1) {
      assert.equal(JSON.parse(init.body).content_type, 'application/octet-stream');
      return success();
    }
    assert.equal(new Headers(init.headers).get('Content-Type'), 'application/octet-stream');
    return new Response(null, { status: 200 });
  };
  const result = await uploadFile(new File(['x'], 'binary'));
  assert.equal(result.content_type, 'application/octet-stream');
});

test('empty file is rejected before any request', async () => {
  globalThis.fetch = async () => assert.fail('must not request');
  await assert.rejects(uploadFile(new File([], 'empty')), e => e.code === 'INVALID_FILE');
});

test('issuance errors stop before PUT and preserve common API error', async () => {
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return Response.json({ success: false, data: null, error: {
      code: 'UNAUTHORIZED', message: '로그인이 필요합니다.', details: [],
    } }, { status: 401 });
  };
  await assert.rejects(uploadFile(file()), e => e.code === 'UNAUTHORIZED' && e.status === 401);
  assert.equal(calls, 1);
});

test('malformed or unsafe grants and inconsistent size never PUT', async () => {
  for (const value of [null, {}, { ...grant, upload_url: 'javascript:alert(1)' },
    { ...grant, upload_url: uploadUrl.replace('https:', 'http:') },
    { ...grant, path: '../other' }, { ...grant, bucket: '../files' },
    { ...grant, expires_in: 0 }, { ...grant, max_file_size_bytes: 0 },
    { ...grant, max_file_size_bytes: 4 }, { ...grant, upload_url: uploadUrl.replace(path, 'other') }]) {
    let calls = 0;
    globalThis.fetch = async () => { calls++; return success(value); };
    await assert.rejects(uploadFile(file()), e => ['INVALID_RESPONSE', 'FILE_TOO_LARGE'].includes(e.code));
    assert.equal(calls, 1);
  }
});

test('Storage rejection hides response body and signed URL and never retries', async () => {
  let calls = 0;
  globalThis.fetch = async () => ++calls === 1 ? success() : new Response(`test-secret ${uploadUrl}`, { status: 413 });
  await assert.rejects(uploadFile(file()), e => {
    assert.equal(e.code, 'UPLOAD_FAILED');
    assert.equal(e.status, 413);
    assert.equal(e.upload_uncertain, false);
    assert.ok(!e.message.includes('test-secret'));
    assert.ok(!e.message.includes('test-token'));
    return true;
  });
  assert.equal(calls, 2);
});

test('upload transport failure is uncertain and is not retried', async () => {
  let calls = 0;
  globalThis.fetch = async () => {
    if (++calls === 1) return success();
    throw new TypeError(`test-secret ${uploadUrl}`);
  };
  await assert.rejects(uploadFile(file()), e => e.code === 'UPLOAD_NETWORK_ERROR' && e.upload_uncertain && !e.message.includes('test-token'));
  assert.equal(calls, 2);
});

test('abort is preserved during either stage', async () => {
  const abort = new DOMException('Cancelled', 'AbortError');
  for (const at of [1, 2]) {
    let calls = 0;
    globalThis.fetch = async () => { if (++calls === at) throw abort; return success(); };
    await assert.rejects(uploadFile(file()), e => e === abort);
    assert.equal(calls, at);
  }
});
