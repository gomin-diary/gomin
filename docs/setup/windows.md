# Windows 설치

PowerShell에서 저장소 루트로 이동한 뒤 실행합니다. Node.js가 없어도 실행할 수 있습니다.

```powershell
./scripts/setup.cmd
```

## 준비 사항

- Windows PowerShell 5.1 이상
- nvm 설치·전환이 가능한 관리자 계정: 일반 권한 PowerShell에서 시작해도 UAC로 같은 계정을 승격할 수 있습니다.
- WinGet: Microsoft Store의 **앱 설치 관리자(App Installer)**가 제공합니다.
- 백엔드를 실행한다면 Python 3.12 이상: Python 설치 시 Python Launcher도 설치하면 `py -3`로 찾을 수 있습니다.
- 백엔드를 실행한다면 Docker Desktop: WSL2 기반 Linux 컨테이너 엔진을 켜 둡니다.

프론트엔드만 설치하면 Python·Docker·WSL2가 필요하지 않습니다.

```powershell
./scripts/setup.cmd frontend
```

## nvm·Node.js 자동 설치

공통 진입 파일은 PowerShell을 실행합니다. nvm-windows가 없으면 WinGet의 `CoreyButler.NVMforWindows` 패키지를 설치합니다. 이후 `.nvmrc`에 맞는 Node 배포 버전을 조회해 설치하고 선택합니다.

nvm 설치·버전 전환 전용 하위 프로세스에서 Windows 관리자 권한 확인 창이 표시될 수 있습니다. 프로젝트의 npm·Python 의존성 설치는 호출한 터미널의 권한으로 수행합니다. 일반 PowerShell에서 시작하면 프로젝트 의존성을 관리자 권한으로 설치할 필요가 없습니다. [nvm-windows의 권한·설치 설명](https://github.com/nvm-windows/nvm#installation--upgrades), [WinGet 설치 명령](https://learn.microsoft.com/en-us/windows/package-manager/winget/install)을 참고하세요.

권한 확인 창에서 **다른 관리자 계정의 자격 증명**을 입력하면 설치를 시작하기 전에 중단합니다. nvm-windows가 다른 사용자의 폴더에 설치되는 것을 막기 위한 동작입니다. 현재 사용자 계정에 관리자 권한이 필요합니다.

기존에 Node.js를 직접 설치했다면 nvm-windows의 경로와 충돌할 수 있습니다. 스크립트는 기존 Node.js를 자동 삭제하지 않습니다. 설치가 실패하거나 버전이 맞지 않으면 `nvm debug`로 경로를 확인하고 기존 설치를 정리한 뒤 다시 실행하세요.

설치가 끝나면 새 PowerShell을 열고 저장소 루트에서 실행합니다.

```powershell
npm run dev
```

PowerShell 실행 정책이 `npm.ps1`을 차단하면 `npm.cmd run dev`를 사용할 수 있습니다. 공통 설치 파일은 자식 PowerShell에만 `ExecutionPolicy Bypass`를 적용하므로 사용자 전체 실행 정책은 변경하지 않습니다.

## Python 패키지

Windows에서는 `backend/.venv/Scripts/python.exe`를 사용합니다. `uvloop`는 Windows를 지원하지 않아 설치용 임시 요구사항 목록에서 제외하고, 원본 `requirements.txt`는 유지합니다. 임시 파일은 설치 후 삭제합니다.

`PYTHON_BIN` 환경변수로 Python 경로를 지정할 수 있습니다. 기존 가상환경이 있으면 해당 환경의 Python 3.12 이상 여부를 먼저 확인합니다.

[공통 설치 안내](README.md)
