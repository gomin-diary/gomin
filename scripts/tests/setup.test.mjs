import assert from 'node:assert/strict';
import { test } from 'node:test';
import { spawnSync } from 'node:child_process';
import { chmod, cp, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scripts = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
async function fixture(t) {
  const root = await mkdtemp(path.join(tmpdir(), 'gomin setup test '));
  t.after(() => rm(root, { recursive: true, force: true }));
  await cp(scripts, path.join(root, 'scripts'), { recursive: true });
  for (const dir of ['frontend', '.dev', 'nvm', 'bin']) await mkdir(path.join(root, dir), { recursive: true });
  await writeFile(path.join(root, '.nvmrc'), '24\n');
  await writeFile(path.join(root, 'frontend/.env.example'), 'API=example\n');
  await writeFile(path.join(root, 'nvm/nvm.sh'), `nvm() { printf '%s\\n' "nvm $*" >> "$SETUP_TEST_LOG"; }\n`);
  await writeFile(path.join(root, 'bin/npm'), '#!/bin/sh\nprintf "%s\\n" "npm $*" >> "$SETUP_TEST_LOG"\nexit "${SETUP_TEST_NPM_EXIT:-0}"\n');
  await chmod(path.join(root, 'bin/npm'), 0o755);
  const log = path.join(root, 'calls');
  const env = { ...process.env, NVM_DIR: path.join(root, 'nvm'), SETUP_TEST_LOG: log, PATH: `${path.join(root, 'bin')}:${path.dirname(process.execPath)}:${process.env.PATH}` };
  const run = (args, extra = {}) => spawnSync('bash', [path.join(root, 'scripts/setup.cmd'), ...args], { cwd: tmpdir(), env: { ...env, ...extra }, encoding: 'utf8', timeout: 15000 });
  return { root, log, run };
}

test('the common bootstrap shows help without Node or installation', { skip: process.platform === 'win32' }, () => {
  const result = spawnSync('bash', [path.join(scripts, 'setup.cmd'), '--help'], { env: { ...process.env, PATH: '/usr/bin:/bin' }, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /frontend/);
});

test('invalid setup targets fail before installing anything', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  const result = f.run(['unknown']);
  assert.equal(result.status, 1);
  assert.equal(await readFile(f.log, 'utf8').catch(() => ''), '');
});

test('frontend setup reuses nvm, installs dependencies and preserves local env files', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  await writeFile(path.join(f.root, 'frontend/.env.local'), 'API=keep-me\n');
  const result = f.run(['frontend']);
  assert.equal(result.status, 0, result.stderr);
  const calls = await readFile(f.log, 'utf8');
  assert.match(calls, /nvm install 24/);
  assert.match(calls, /npm ci --no-audit --no-fund/);
  assert.match(calls, /npm --prefix frontend ci --no-audit --no-fund/);
  assert.equal(await readFile(path.join(f.root, 'frontend/.env.local'), 'utf8'), 'API=keep-me\n');
});

test('dependency installation failure propagates through the common bootstrap', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  const result = f.run(['frontend'], { SETUP_TEST_NPM_EXIT: '7' });
  assert.equal(result.status, 7, result.stderr);
});

test('setup refuses to replace dependencies while the manager is running', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  await writeFile(path.join(f.root, '.dev/manager.lock'), `${process.pid}\n`);
  const result = f.run(['frontend']);
  assert.equal(result.status, 1, result.stderr);
  assert.doesNotMatch(await readFile(f.log, 'utf8').catch(() => ''), /npm /);
});

for (const shell of (process.platform === 'darwin' ? ['bash', 'zsh'] : ['bash'])) {
  test(`the common file runs directly from ${shell}, including paths with spaces`, { skip: process.platform === 'win32' }, async (t) => {
    const f = await fixture(t);
    const result = spawnSync(shell, ['-c', '"$1" --help', 'setup-test', path.join(f.root, 'scripts/setup.cmd')], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /frontend/);
  });
}

test('a missing nvm is downloaded and installed before project dependencies', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  await rm(path.join(f.root, 'nvm'), { recursive: true });
  // Download is the external boundary: provide a tiny installer, then execute
  // the real Bash bootstrap with an isolated NVM_DIR and PROFILE.
  const installer = `#!/bin/bash
[ -d "$NVM_DIR" ] || exit 1
printf '%s\\n' 'nvm() { printf "%s\\n" "nvm $*" >> "$SETUP_TEST_LOG"; }' > "$NVM_DIR/nvm.sh"
printf '%s\\n' installed >> "$SETUP_TEST_LOG"
`;
  const installerPath = path.join(f.root, 'installer.sh');
  await writeFile(installerPath, installer);
  await writeFile(path.join(f.root, 'bin/curl'), `#!/bin/sh
while [ "$#" -gt 0 ]; do
  if [ "$1" = '-o' ]; then cp "$SETUP_TEST_INSTALLER" "$2"; exit $?; fi
  shift
done
exit 1
`);
  await writeFile(path.join(f.root, 'bin/brew'), '#!/bin/sh\nexit 1\n');
  await chmod(path.join(f.root, 'bin/curl'), 0o755);
  await chmod(path.join(f.root, 'bin/brew'), 0o755);
  const result = f.run(['frontend'], { PROFILE: path.join(f.root, 'profile'), SETUP_TEST_INSTALLER: installerPath });
  assert.equal(result.status, 0, result.stderr);
  const calls = await readFile(f.log, 'utf8');
  assert.ok(calls.indexOf('installed') < calls.indexOf('nvm install 24'));
  assert.ok(calls.indexOf('nvm install 24') < calls.indexOf('npm ci'));
  assert.equal(await readFile(path.join(f.root, 'frontend/.env.local'), 'utf8'), 'API=example\n');
});

test('Windows PowerShell can run the common bootstrap and parse all setup scripts', { skip: process.platform !== 'win32' }, () => {
  const result = spawnSync('powershell.exe', ['-NoProfile', '-Command', `
    $ErrorActionPreference = 'Stop'
    Get-ChildItem $env:SETUP_TEST_SCRIPTS -Filter '*.ps1' | ForEach-Object {
      $ParseErrors = $null
      [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$null, [ref]$ParseErrors)
      if ($ParseErrors.Count) { throw ($ParseErrors | Out-String) }
    }
    & (Join-Path $env:SETUP_TEST_SCRIPTS 'setup.cmd') --help
    exit $LASTEXITCODE
  `], { encoding: 'utf8', env: { ...process.env, SETUP_TEST_SCRIPTS: scripts } });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /frontend/);
});

test('an old Node on PATH does not block installing the requested Node version', { skip: process.platform === 'win32' }, async (t) => {
  const f = await fixture(t);
  await writeFile(path.join(f.root, 'bin/node'), `#!/bin/sh
if ! grep -q 'nvm use 24' "$SETUP_TEST_LOG" 2>/dev/null; then exit 99; fi
exec "${process.execPath}" "$@"
`);
  await chmod(path.join(f.root, 'bin/node'), 0o755);
  const result = f.run(['frontend']);
  assert.equal(result.status, 0, result.stderr);
  assert.match(await readFile(f.log, 'utf8'), /npm --prefix frontend ci/);
});

test('Windows rejects elevation into another account before installing anything', { skip: process.platform !== 'win32' }, () => {
  const result = spawnSync('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', path.join(scripts, 'setup-node.ps1'), '-CallerSid', 'S-1-0-0'], { encoding: 'utf8' });
  assert.equal(result.status, 1);
  assert.doesNotMatch(result.stdout, /winget|Downloading|Installing/);
});
