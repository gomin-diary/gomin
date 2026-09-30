# This helper runs elevated only for the nvm-windows / Node installation.
param([Parameter(Mandatory = $true)][string]$CallerSid)
$ErrorActionPreference = 'Stop'
try {
  if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -ne $CallerSid) {
    throw '다른 관리자 계정으로 설치할 수 없습니다. nvm-windows는 사용자별 설치입니다. 현재 사용자에게 관리자 권한을 부여한 뒤 다시 실행하세요. docs/local-development/setup/windows.md'
  }
  $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
  $RequestedVersion = (Get-Content (Join-Path $ProjectRoot '.nvmrc') -Raw).Trim()
  if ($RequestedVersion -notmatch '^\d+(\.\d+){0,2}$') { throw '.nvmrc must contain a numeric Node.js version.' }
  if (-not (Get-Command nvm.exe -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
      throw 'WinGet이 필요합니다. Microsoft Store에서 앱 설치 관리자(App Installer)를 설치한 뒤 다시 실행하세요. docs/local-development/setup/windows.md'
    }
    Write-Host 'nvm-windows를 설치합니다.'
    & winget.exe install --id CoreyButler.NVMforWindows --exact --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "nvm-windows 설치 실패: $LASTEXITCODE" }
  }
  foreach ($Name in @('NVM_HOME', 'NVM_SYMLINK')) {
    $Value = [Environment]::GetEnvironmentVariable($Name, 'User')
    if (-not $Value) { $Value = [Environment]::GetEnvironmentVariable($Name, 'Machine') }
    if ($Value) { Set-Item "Env:$Name" $Value }
  }
  $env:Path = "$env:NVM_HOME;$env:NVM_SYMLINK;" + [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ";$env:Path"
  if (-not (Get-Command nvm.exe -ErrorAction SilentlyContinue)) { throw 'nvm-windows를 찾을 수 없습니다. 새 터미널에서 다시 실행하세요.' }
  # Resolve .nvmrc's major version to an exact version for nvm-windows.
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $Versions = Invoke-RestMethod 'https://nodejs.org/dist/index.json'
  $Selected = $Versions | Where-Object { $_.version.TrimStart('v') -match ('^' + [regex]::Escape($RequestedVersion) + '(\.|$)') } | Select-Object -First 1
  if (-not $Selected) { throw "Node.js $RequestedVersion 배포 버전을 찾을 수 없습니다." }
  $NodeVersion = $Selected.version.TrimStart('v')
  & nvm.exe install $NodeVersion
  if ($LASTEXITCODE -ne 0) { throw 'Node.js 설치에 실패했습니다.' }
  & nvm.exe use $NodeVersion
  if ($LASTEXITCODE -ne 0) { throw 'Node.js 버전 전환에 실패했습니다. nvm debug로 기존 Node.js와의 경로 충돌을 확인하세요.' }
  $InstalledVersion = & node.exe --version
  if ($LASTEXITCODE -ne 0 -or $InstalledVersion.Trim() -ne "v$NodeVersion") { throw 'Node.js 경로가 일치하지 않습니다. nvm debug로 확인하세요.' }
  exit 0
} catch {
  [Console]::Error.WriteLine($_.Exception.Message)
  exit 1
}
