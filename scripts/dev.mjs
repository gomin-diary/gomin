import { spawn, execFile } from 'node:child_process';
import { createServer, connect } from 'node:net';
import { randomBytes } from 'node:crypto';
import { mkdir, open, readFile, unlink, writeFile, access } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const stateDir = path.join(root, '.dev');
const lockPath = path.join(stateDir, 'manager.lock');
const guardPath = path.join(stateDir, 'manager.guard');
const endpointPath = path.join(stateDir, 'control.json');
const target = process.argv[2] ?? 'all';
const targets = ['frontend', 'backend', 'all'];
const windows = process.platform === 'win32';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const exited = (child) => child.exitCode !== null || child.signalCode !== null;
const setupHint = '저장소 루트에서 ./scripts/setup.cmd를 실행하세요.';

async function exists(file) {
  try { await access(file); return true; } catch { return false; }
}

function isAlive(pid) {
  if (!Number.isSafeInteger(pid) || pid <= 0) return false;
  try { process.kill(pid, 0); return true; } catch (error) { return error.code === 'EPERM'; }
}

// Detached POSIX children share a process group with their own descendants.
// Wait for the group, not just its leader (Next.js/Uvicorn may have workers).
async function stopProcess(child) {
  if (!child?.pid) return;
  if (windows) {
    if (exited(child)) return;
    await new Promise((resolve, reject) => {
      execFile('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, timeout: 6000 }, (error) => {
        if (error && !exited(child)) reject(new Error(`프로세스 ${child.pid} 종료 실패: ${error.message}`));
        else resolve();
      });
    });
    return;
  }
  const groupAlive = () => {
    try { process.kill(-child.pid, 0); return true; } catch (error) { return error.code === 'EPERM'; }
  };
  if (!groupAlive()) return;
  try { process.kill(-child.pid, 'SIGTERM'); } catch (error) { if (error.code !== 'ESRCH') throw error; }
  const deadline = Date.now() + 5000;
  while (groupAlive() && Date.now() < deadline) await sleep(25);
  if (groupAlive()) {
    try { process.kill(-child.pid, 'SIGKILL'); } catch (error) { if (error.code !== 'ESRCH') throw error; }
    const killDeadline = Date.now() + 1000;
    while (!exited(child) && Date.now() < killDeadline) await sleep(25);
  }
}

function redact(text) {
  return text.replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, '[키 숨김]')
    .replace(/sb_secret_[A-Za-z0-9_-]+/g, '[키 숨김]');
}

async function runCommand(command, args, { signal, label, capture = false } = {}) {
  signal.throwIfAborted();
  const child = spawn(command, args, {
    cwd: root, detached: !windows, windowsHide: true,
    stdio: ['ignore', capture ? 'pipe' : 'ignore', 'pipe'],
  });
  let stdout = '';
  let stderr = '';
  child.stdout?.setEncoding('utf8');
  child.stdout?.on('data', (chunk) => { stdout += chunk; });
  child.stderr.setEncoding('utf8');
  child.stderr.on('data', (chunk) => { stderr = (stderr + chunk).slice(-12000); });
  const startedAt = Date.now();
  const progress = setInterval(() => console.log(`${label} 진행 중 (${Math.floor((Date.now() - startedAt) / 1000)}초). 첫 실행은 다운로드로 시간이 걸릴 수 있습니다.`), 10000);
  let cancelling;
  const abort = () => { cancelling ??= stopProcess(child).catch(() => {}); };
  signal.addEventListener('abort', abort, { once: true });
  try {
    await new Promise((resolve, reject) => {
      child.once('error', (error) => reject(new Error(`${label} 실행 실패: ${error.message}`)));
      child.once('close', (code, childSignal) => {
        if (code === 0) resolve();
        else reject(new Error(`${label} 실패 (${code ?? childSignal}). ${redact(stderr).trim()}`));
      });
    });
    signal.throwIfAborted();
    return stdout;
  } finally {
    clearInterval(progress);
    signal.removeEventListener('abort', abort);
    await cancelling;
  }
}

function parseEnv(text) {
  const result = {};
  for (const line of text.split(/\r?\n/)) {
    const match = line.match(/^\s*(?:export\s+)?([A-Za-z_][\w.]*)\s*=\s*(.*?)\s*$/);
    if (!match) continue;
    let value = match[2];
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) value = value.slice(1, -1);
    result[match[1]] = value;
  }
  return result;
}

async function prepareLocalEnvironment(signal) {
  // Invoke the pinned package's JS entry directly; .cmd shims require a shell
  // and lose argument quoting when the repository path contains spaces.
  const cli = path.join(root, 'node_modules', 'supabase', 'dist', 'supabase.js');
  if (!await exists(cli)) throw new Error(`Supabase CLI가 없습니다. ${setupHint}`);
  console.log('로컬 Supabase를 준비합니다. Docker가 실행 중이어야 합니다.');
  await runCommand(process.execPath, [cli, 'start'], { signal, label: 'Supabase 시작' });
  await runCommand(process.execPath, [cli, 'migration', 'up', '--local'], { signal, label: 'DB 마이그레이션' });
  const status = await runCommand(process.execPath, [cli, 'status', '-o', 'env'], { signal, label: '로컬 연결 정보 조회', capture: true });
  const values = parseEnv(status);
  const apiUrl = values.API_URL || values.SUPABASE_URL || values['api.url'];
  const secret = values.SECRET_KEY || values.SUPABASE_SECRET_KEY || values['auth.secret_key'] || values.SERVICE_ROLE_KEY || values.SUPABASE_SERVICE_ROLE_KEY || values['auth.service_role_key'];
  if (!apiUrl || !secret) throw new Error('로컬 Supabase URL 또는 서버 키를 읽지 못했습니다. npm run supabase:status로 상태를 확인하세요.');
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(new URL(apiUrl).hostname)) throw new Error('개발 실행기는 로컬 Supabase URL만 허용합니다.');
  return { ...process.env, SUPABASE_URL: apiUrl, SUPABASE_SECRET_KEY: secret, CORS_ORIGINS: '["http://127.0.0.1:3000","http://localhost:3000"]' };
}

function checkPort(port) {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.once('error', (error) => reject(new Error(`${port} 포트를 사용할 수 없습니다 (${error.code}). 해당 포트를 사용하는 서버를 직접 종료하세요.`)));
    server.listen(port, '127.0.0.1', () => server.close(resolve));
  });
}

async function restartServers(requested, processes, signal) {
  signal.throwIfAborted();
  const names = requested === 'all' ? ['frontend', 'backend'] : [requested];
  const commands = {};
  const environments = {};
  if (names.includes('frontend')) {
    const nextCli = path.join(root, 'frontend', 'node_modules', 'next', 'dist', 'bin', 'next');
    if (!await exists(nextCli)) throw new Error(`프론트엔드 의존성이 없습니다. ${setupHint}`);
    commands.frontend = [process.execPath, [nextCli, 'dev', '--hostname', '127.0.0.1', '--port', '3000']];
    environments.frontend = { ...process.env, NEXT_PUBLIC_API_BASE_URL: 'http://127.0.0.1:8000' };
  }
  if (names.includes('backend')) {
    const python = path.join(root, 'backend', '.venv', windows ? 'Scripts/python.exe' : 'bin/python');
    if (!await exists(python)) throw new Error(`백엔드 가상환경이 없습니다. ${setupHint}`);
    environments.backend = await prepareLocalEnvironment(signal);
    commands.backend = [python, ['-m', 'uvicorn', 'app.main:app', '--reload', '--host', '127.0.0.1', '--port', '8000']];
  }
  signal.throwIfAborted();
  for (const name of names) {
    await stopProcess(processes[name]);
    delete processes[name];
  }
  for (const name of names) await checkPort(name === 'frontend' ? 3000 : 8000);
  const started = [];
  try {
    for (const name of names) {
      signal.throwIfAborted();
      const [command, args] = commands[name];
      const child = spawn(command, args, { cwd: path.join(root, name), env: environments[name], detached: !windows, stdio: 'inherit', windowsHide: true });
      processes[name] = child;
      started.push(name);
      await new Promise((resolve, reject) => {
        child.once('spawn', resolve);
        child.once('error', reject);
      });
    }
    signal.throwIfAborted();
  } catch (error) {
    for (const name of started) { await stopProcess(processes[name]); delete processes[name]; }
    throw error;
  }
  console.log(`${requested}: 시작 요청을 처리했습니다. 서버 준비 상태는 아래 로그를 확인하세요.`);
}

function sendRequest(endpoint, payload) {
  return new Promise((resolve, reject) => {
    const client = connect(endpoint.port, '127.0.0.1');
    let data = '';
    const timer = setTimeout(() => client.destroy(new Error('실행기 응답 시간 초과. 기존 개발 터미널의 로그를 확인하세요.')), 600000);
    client.on('connect', () => client.write(`${JSON.stringify({ ...payload, token: endpoint.token })}\n`));
    client.on('data', (chunk) => {
      data += chunk;
      if (!data.includes('\n')) return;
      try { resolve(JSON.parse(data.split('\n')[0])); } catch (error) { reject(error); }
      client.end();
    });
    client.on('error', reject);
    client.on('close', () => { clearTimeout(timer); reject(new Error('응답 전에 실행기 연결이 종료됐습니다.')); });
  });
}

async function requestRestart() {
  // The lock is published just before the endpoint. Allow a simultaneous
  // invocation to wait for that short startup window.
  let endpoint;
  for (let attempt = 0; attempt < 20; attempt++) {
    try { endpoint = JSON.parse(await readFile(endpointPath, 'utf8')); break; }
    catch (error) { if (attempt === 19) throw error; await sleep(100); }
  }
  const result = await sendRequest(endpoint, { target });
  console.log(result.message);
  return result.ok ? 0 : 1;
}

async function supervisor() {
  const processes = {};
  const controller = new AbortController();
  const { signal } = controller;
  const token = randomBytes(24).toString('hex');
  const sockets = new Set();
  let queue = Promise.resolve();
  const enqueue = (work) => {
    const pending = queue.then(() => { signal.throwIfAborted(); return work(); });
    queue = pending.catch(() => {});
    return pending;
  };
  const stop = () => { if (!signal.aborted) { console.log('진행 중인 작업을 취소하고 앱 서버를 종료합니다.'); controller.abort(); } };
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
  const server = createServer((socket) => {
    sockets.add(socket);
    socket.on('close', () => sockets.delete(socket));
    socket.on('error', () => {});
    socket.setTimeout(600000, () => socket.destroy());
    let data = '';
    socket.on('data', async (chunk) => {
      data += chunk;
      if (data.length > 8192) { socket.destroy(); return; }
      if (!data.includes('\n')) return;
      socket.removeAllListeners('data');
      let response;
      try {
        const request = JSON.parse(data.split('\n')[0]);
        if (request.token !== token) throw new Error('인증되지 않은 실행 요청입니다.');
        if (!targets.includes(request.target)) throw new Error('실행 대상은 frontend, backend, all 중 하나입니다.');
        await enqueue(() => restartServers(request.target, processes, signal));
        response = { ok: true, message: `${request.target}: 시작 요청을 처리했습니다. 서버 로그는 기존 개발 터미널을 확인하세요.` };
      } catch (error) { response = { ok: false, message: signal.aborted ? '실행기가 종료 중입니다.' : error.message }; }
      socket.end(`${JSON.stringify(response)}\n`);
    });
  });
  try {
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
    await writeFile(endpointPath, JSON.stringify({ port: server.address().port, token }), { mode: 0o600 });
    await enqueue(() => restartServers(target, processes, signal));
    console.log('\n개발 실행기가 켜져 있습니다. 다른 터미널에서 npm run dev:frontend / dev:backend / dev:all로 재시작할 수 있습니다.\n웹: http://127.0.0.1:3000 · API 문서: http://127.0.0.1:8000/docs\n종료: 이 터미널에서 Ctrl+C\n');
    while (!signal.aborted) {
      await enqueue(async () => {
        for (const [name, child] of Object.entries(processes)) {
          if (exited(child)) {
            await stopProcess(child);
            delete processes[name];
            console.log(`${name} 서버가 종료됐습니다. 다시 시작하려면 npm run dev:${name}을 실행하세요.`);
          }
        }
      });
      await sleep(250);
    }
  } catch (error) {
    if (!signal.aborted) throw error;
  } finally {
    controller.abort();
    server.close();
    await queue;
    try {
      const results = await Promise.allSettled(Object.values(processes).map(stopProcess));
      for (const result of results) if (result.status === 'rejected') throw result.reason;
      console.log('앱 서버 정리를 마쳤습니다. Supabase도 중지하려면 npm run supabase:stop을 실행하세요.');
    } finally {
      for (const socket of sockets) socket.destroy();
      process.off('SIGINT', stop);
      process.off('SIGTERM', stop);
    }
  }
  return 0;
}

// Serialize creation AND stale-lock recovery. A stale guard fails closed:
// deleting it automatically could let two recoverers remove a new owner's lock.
async function acquireManagerLock() {
  let guard;
  for (let attempt = 0; attempt < 50; attempt++) {
    try { guard = await open(guardPath, 'wx', 0o600); break; }
    catch (error) {
      if (error.code !== 'EEXIST') throw error;
      await sleep(100);
    }
  }
  if (!guard) throw new Error('실행기 잠금을 확인할 수 없습니다. docs/local-development/setup-runtime-troubleshooting.md의 manager.guard 안내를 확인하세요.');
  try {
    await guard.writeFile(`${process.pid}\n`);
    const pid = Number((await readFile(lockPath, 'utf8').catch(() => '0')).trim());
    if (isAlive(pid)) return false;
    await unlink(endpointPath).catch((error) => { if (error.code !== 'ENOENT') throw error; });
    await writeFile(lockPath, `${process.pid}\n`, { mode: 0o600 });
    return true;
  } finally {
    await guard.close();
    await unlink(guardPath);
  }
}

async function main() {
  process.chdir(root);
  if (target === '--check-idle') {
    const pid = Number((await readFile(lockPath, 'utf8').catch(() => '0')).trim());
    if (isAlive(pid)) throw new Error('개발 실행기가 켜져 있습니다. 기존 개발 터미널에서 Ctrl+C로 종료한 뒤 설치를 다시 실행하세요.');
    if (await exists(guardPath)) throw new Error('실행기 잠금 작업이 진행 중입니다. 잠시 후 다시 시도하세요. docs/local-development/setup-runtime-troubleshooting.md');
    return 0;
  }
  if (!targets.includes(target) || process.argv.length > 3) throw new Error('사용법: node scripts/dev.mjs [frontend|backend|all]');
  await mkdir(stateDir, { recursive: true, mode: 0o700 });
  if (!await acquireManagerLock()) {
    try { return await requestRestart(); }
    catch (requestError) {
      const pid = Number((await readFile(lockPath, 'utf8').catch(() => '0')).trim());
      if (isAlive(pid)) throw new Error(`기존 실행기에 연결하지 못했습니다. 개발 터미널을 확인하세요: ${requestError.message}`);
      return main();
    }
  }
  try { return await supervisor(); }
  finally {
    await unlink(endpointPath).catch(() => {});
    await unlink(lockPath).catch(() => {});
  }
}

main().then((code) => { process.exitCode = code; }).catch((error) => {
  console.error(redact(error.message));
  process.exitCode = 1;
});
