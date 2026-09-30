$ErrorActionPreference = 'Stop'
# Parse raw arguments so --help works through cmd.exe and PowerShell -File.
$SetupArguments = @($args)
$Target = if ($SetupArguments.Count -eq 0) { 'all' } else { [string]$SetupArguments[0] }
if ($Target -eq '--help' -or $Target -eq '-h') {
  Write-Host '사용법: ./scripts/setup.cmd [all|frontend|backend]'
  Write-Host 'nvm·Node.js와 선택한 대상의 의존성을 설치합니다. 기본값: all'
  exit 0
}
try {
  if ($Target -notin @('all', 'frontend', 'backend') -or $SetupArguments.Count -gt 1) { throw '사용법: ./scripts/setup.cmd [all|frontend|backend]' }
  $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
  Set-Location $ProjectRoot
  # The bootstrap must also work when the existing Node version is too old.
  if (Test-Path '.dev/manager.guard') { throw '실행기 잠금 작업이 진행 중입니다. docs/development/troubleshooting.md' }
  if (Test-Path '.dev/manager.lock') {
    $ManagerProcessId = 0
    $ManagerPidText = (Get-Content '.dev/manager.lock' -Raw).Trim()
    if ([int]::TryParse($ManagerPidText, [ref]$ManagerProcessId) -and $ManagerProcessId -gt 0) {
      if (Get-Process -Id $ManagerProcessId -ErrorAction SilentlyContinue) { throw '개발 실행기가 켜져 있습니다. 기존 개발 터미널에서 Ctrl+C로 종료한 뒤 설치하세요.' }
    }
  }
  Write-Host 'nvm·Node.js를 준비합니다. Windows 권한 확인 창이 표시될 수 있습니다.'
  $NodeSetup = Join-Path $PSScriptRoot 'setup-node.ps1'
  $Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $Principal = New-Object Security.Principal.WindowsPrincipal($Identity)
  $IsAdmin = $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  $StartOptions = @{
    FilePath = 'powershell.exe'
    ArgumentList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"{0}"' -f $NodeSetup), '-CallerSid', $Identity.User.Value)
    Wait = $true
    PassThru = $true
  }
  if (-not $IsAdmin) { $StartOptions.Verb = 'RunAs' }
  $NodeSetupProcess = Start-Process @StartOptions
  if ($NodeSetupProcess.ExitCode -ne 0) { throw 'nvm·Node.js 준비에 실패했습니다. docs/setup/windows.md를 확인한 뒤 다시 실행하세요.' }
  foreach ($Name in @('NVM_HOME', 'NVM_SYMLINK')) {
    $Value = [Environment]::GetEnvironmentVariable($Name, 'User')
    if (-not $Value) { $Value = [Environment]::GetEnvironmentVariable($Name, 'Machine') }
    if ($Value) { Set-Item "Env:$Name" $Value }
  }
  $env:Path = "$env:NVM_HOME;$env:NVM_SYMLINK;" + [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ";$env:Path"
  & node.exe scripts/dev.mjs --check-idle
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  if ($Target -ne 'frontend') {
    if (-not (Get-Command docker.exe -ErrorAction SilentlyContinue)) { throw 'Docker Desktop을 설치·실행하세요. docs/setup/windows.md' }
    & docker.exe info *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Docker에 연결할 수 없습니다. Docker Desktop의 Linux 컨테이너 엔진을 실행하세요.' }
    $VenvPython = Join-Path $ProjectRoot 'backend/.venv/Scripts/python.exe'
    $PythonCommand = $null
    $PythonArgs = @()
    $Candidates = @()
    if (Test-Path $VenvPython) { $Candidates = @(@{ Command = $VenvPython; Args = @() }) }
    elseif ($env:PYTHON_BIN) { $Candidates = @(@{ Command = $env:PYTHON_BIN; Args = @() }) }
    else { $Candidates = @(@{ Command = 'py'; Args = @('-3') }, @{ Command = 'python3'; Args = @() }, @{ Command = 'python'; Args = @() }, @{ Command = 'py'; Args = @('-3.12') }, @{ Command = 'python3.12'; Args = @() }) }
    foreach ($Candidate in $Candidates) {
      try {
        $CandidateCommand = $Candidate.Command
        $CandidateArgs = @($Candidate.Args)
        & $CandidateCommand @CandidateArgs -c 'import sys; sys.exit(sys.version_info[:2] < (3, 12))' 2>$null
        if ($LASTEXITCODE -eq 0) { $PythonCommand = $CandidateCommand; $PythonArgs = $CandidateArgs; break }
      } catch {}
    }
    if (-not $PythonCommand) { throw 'Python 3.12 이상이 필요합니다. 기존 backend/.venv도 확인하세요. docs/setup/windows.md' }
  }

  Write-Host '프로젝트 의존성을 설치합니다.'
  & npm.cmd ci --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  if ($Target -ne 'backend') {
    & npm.cmd --prefix frontend ci --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if (-not (Test-Path 'frontend/.env.local')) { Copy-Item frontend/.env.example frontend/.env.local }
  }
  if ($Target -ne 'frontend') {
    if (-not (Test-Path $VenvPython)) {
      & $PythonCommand @PythonArgs -m venv backend/.venv
      if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    $TempRequirements = Join-Path ([IO.Path]::GetTempPath()) ("gomin-requirements-{0}.txt" -f [guid]::NewGuid())
    try {
      Get-Content backend/requirements.txt | Where-Object { $_ -notmatch '^uvloop==' } | Set-Content $TempRequirements -Encoding ascii
      & $VenvPython -m pip install -r $TempRequirements
      if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally { Remove-Item $TempRequirements -ErrorAction SilentlyContinue }
    if (-not (Test-Path 'backend/.env')) { Copy-Item backend/.env.example backend/.env }
  }
  Write-Host "설치 완료. 새 터미널을 열고 저장소 루트에서 실행하세요: npm run dev:$Target"
  Write-Host '설치 단계에서는 앱 서버와 Supabase를 시작하지 않습니다.'
  exit 0
} catch {
  [Console]::Error.WriteLine($_.Exception.Message)
  exit 1
}
