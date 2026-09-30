import assert from 'node:assert/strict';
import { test } from 'node:test';
import { spawn } from 'node:child_process';
import { cp, mkdir, mkdtemp, readFile, writeFile, chmod, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scripts = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(check, label, timeout = 4000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (await check()) return;
    await delay(25);
  }
  throw new Error(`Timed out: ${label}`);
}
function alive(pid) {
  try { process.kill(pid, 0); return true; } catch { return false; }
}
async function fixture(t) {
  const root = await mkdtemp(path.join(tmpdir(), 'gomin dev test '));
  await cp(scripts, path.join(root, 'scripts'), { recursive: true });
  for (const dir of ['.dev', 'frontend/node_modules/next/dist/bin', 'backend/.venv/bin', 'node_modules/.bin', 'node_modules/supabase/dist']) {
    await mkdir(path.join(root, dir), { recursive: true });
  }
  const app = `import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(process.cwd(), '..');
fs.appendFileSync(path.join(root, '.dev/starts'), JSON.stringify({ name: path.basename(process.cwd()), pid: process.pid }) + '\\n');
setInterval(() => {}, 1000);\n`;
  await writeFile(path.join(root, 'frontend/node_modules/next/package.json'), '{"type":"module"}');
  await writeFile(path.join(root, 'frontend/node_modules/next/dist/bin/next'), app);
  const python = path.join(root, 'backend/.venv/bin/python');
  await writeFile(python, `#!${process.execPath}\n${app.replaceAll("import fs from 'node:fs';", "const fs = require('node:fs');").replaceAll("import path from 'node:path';", "const path = require('node:path');")}`);
  await chmod(python, 0o755);
  const cli = `#!${process.execPath}
const fs = require('node:fs');
fs.appendFileSync('.dev/cli-pids', process.pid + '\\n');
if (fs.existsSync('.dev/fail-supabase')) process.exit(1);
if (process.argv[2] === 'status') console.log('API_URL="http://127.0.0.1:54321"\\nSECRET_KEY="test-only"');
if (process.argv[2] === 'start' && fs.existsSync('.dev/hold-supabase')) {
  fs.writeFileSync('.dev/preparing', '1');
  const timer = setInterval(() => { if (!fs.existsSync('.dev/hold-supabase')) clearInterval(timer); }, 25);
}
`;
  await writeFile(path.join(root, 'node_modules/.bin/supabase'), cli);
  await chmod(path.join(root, 'node_modules/.bin/supabase'), 0o755);
  await writeFile(path.join(root, 'node_modules/supabase/dist/supabase.js'), cli);
  // Keep the application's fixed port probes away from the user's running servers.
  await writeFile(path.join(root, 'ports.mjs'), `import { Server } from 'node:net';
const listen = Server.prototype.listen;
Server.prototype.listen = function (port, ...args) { return listen.call(this, port === 3000 || port === 8000 ? 0 : port, ...args); };`);
  const children = [];
  const launch = (target) => {
    const child = spawn(process.execPath, ['--import', './ports.mjs', 'scripts/dev.mjs', target], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
    child.output = '';
    child.stdout.on('data', (chunk) => { child.output += chunk; });
    child.stderr.on('data', (chunk) => { child.output += chunk; });
    child.done = new Promise((resolve) => child.once('exit', (code, signal) => resolve({ code, signal })));
    children.push(child);
    return child;
  };
  const entries = async () => (await readFile(path.join(root, '.dev/starts'), 'utf8').catch(() => '')).trim().split('\n').filter(Boolean).map(JSON.parse);
  t.after(async () => {
    for (const child of children) if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
    for (const { pid } of await entries()) { try { process.kill(-pid, 'SIGKILL'); } catch {} }
    const cliPids = await readFile(path.join(root, '.dev/cli-pids'), 'utf8').catch(() => '');
    for (const pid of cliPids.trim().split('\n').filter(Boolean)) { try { process.kill(Number(pid), 'SIGKILL'); } catch {} }
    await Promise.all(children.map((child) => child.done));
    await rm(root, { recursive: true, force: true });
  });
  return { root, launch, entries, python };
}

// Real child processes and control sockets exercise the manager, without Docker or application dependencies.
test('a failed restart returns a nonzero command exit code', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  const manager = f.launch('frontend');
  await until(async () => (await f.entries()).length === 1, 'frontend started');
  await writeFile(path.join(f.root, '.dev/fail-supabase'), '1');
  const request = f.launch('backend');
  await until(() => request.exitCode !== null, 'failed request completed');
  assert.equal(request.exitCode, 1, request.output);
  assert.equal(manager.exitCode, null);
});

test('a signal-exited server can be restarted and the manager can stop', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  const manager = f.launch('frontend');
  await until(async () => (await f.entries()).length === 1, 'frontend started');
  const [{ pid }] = await f.entries();
  process.kill(pid, 'SIGTERM');
  await until(() => !alive(pid), 'first server exited');
  const request = f.launch('frontend');
  await until(() => request.exitCode !== null, 'restart completed');
  assert.equal(request.exitCode, 0, request.output);
  await until(async () => (await f.entries()).length === 2, 'replacement started');
  manager.kill('SIGINT');
  await until(() => manager.exitCode !== null, 'manager stopped');
  assert.equal(manager.exitCode, 0, manager.output);
  assert.ok((await f.entries()).every(({ pid: childPid }) => !alive(childPid)));
});

test('shutdown cancels Supabase preparation without starting an app afterwards', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  await writeFile(path.join(f.root, '.dev/hold-supabase'), '1');
  const manager = f.launch('all');
  await until(async () => (await readFile(path.join(f.root, '.dev/preparing'), 'utf8').catch(() => '')) === '1', 'Supabase preparation');
  manager.kill('SIGINT');
  await rm(path.join(f.root, '.dev/hold-supabase'));
  await until(() => manager.exitCode !== null, 'cancelled startup');
  assert.equal(manager.exitCode, 0, manager.output);
  assert.deepEqual(await f.entries(), []);
});

test('an asynchronous spawn error cleans up the apps already started', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  await chmod(f.python, 0o644);
  const manager = f.launch('all');
  await until(() => manager.exitCode !== null, 'spawn failure');
  assert.equal(manager.exitCode, 1);
  await until(async () => (await f.entries()).every(({ pid }) => !alive(pid)), 'rollback stopped all apps');
  assert.equal(await readFile(path.join(f.root, '.dev/manager.lock'), 'utf8').catch(() => ''), '');
  assert.doesNotMatch(manager.output, /Unhandled 'error' event/);
});

test('simultaneous restarts leave exactly one managed server', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  const manager = f.launch('frontend');
  await until(async () => (await f.entries()).length === 1, 'frontend started');
  const requests = [f.launch('frontend'), f.launch('frontend')];
  await until(() => requests.every((child) => child.exitCode !== null), 'concurrent requests');
  assert.ok(requests.every((child) => child.exitCode === 0), requests.map((child) => child.output).join('\n'));
  await until(async () => (await f.entries()).filter(({ pid }) => alive(pid)).length === 1, 'one live server');
  manager.kill('SIGINT');
  await until(() => manager.exitCode !== null, 'manager stopped');
  assert.ok((await f.entries()).every(({ pid }) => !alive(pid)));
});

test('simultaneous launches recover a stale lock with only one supervisor', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  await writeFile(path.join(f.root, '.dev/manager.lock'), '2147483647\n');
  const invocations = Array.from({ length: 4 }, () => f.launch('frontend'));
  await until(() => invocations.filter((child) => child.exitCode !== null).length === 3, 'three callers completed after stale recovery', 6500);
  assert.ok(invocations.filter((child) => child.exitCode !== null).every((child) => child.exitCode === 0), invocations.map((child) => child.output).join('\n'));
  await until(async () => (await f.entries()).filter(({ pid }) => alive(pid)).length === 1, 'one live app after stale recovery');
});
