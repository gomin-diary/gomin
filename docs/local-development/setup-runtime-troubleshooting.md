# 로컬 개발환경 설치·실행 문제 해결

| 증상 | 확인 및 조치 |
| --- | --- |
| macOS/Linux에서 `setup.cmd` 실행 권한 오류 | `chmod +x scripts/setup.cmd` 후 같은 명령으로 재시도 |
| nvm 다운로드 실패 | 인터넷·프록시 설정과 `curl`/`wget` 설치 확인 후 재시도 |
| 설치했지만 `node` 또는 `npm`을 찾지 못함 | 새 터미널을 열어 PATH·셸 설정 적용 |
| Windows에서 WinGet을 찾지 못함 | Microsoft Store의 앱 설치 관리자(App Installer) 설치·업데이트 |
| Windows Node 버전이 맞지 않음 | `nvm debug`로 기존 Node 설치와 PATH 충돌 확인 |
| Windows의 관리자 권한 창을 취소함 | 설치 명령을 다시 실행하고 nvm 설치·전환에 필요한 권한 확인 |
| PowerShell에서 `npm.ps1` 실행이 차단됨 | `npm.cmd run dev` 사용 |
| Python 버전 오류 | Python 3.12 이상 설치 확인. 3.12 미만인 기존 `backend/.venv`는 따로 옮긴 뒤 재설치 |
| Linux에서 venv 생성 실패 | 사용하는 Python 버전(3.12 이상)에 맞는 venv 패키지 설치 |
| Docker에 연결하지 못함 | Docker 실행 및 현재 사용자의 Docker 접근 권한 확인 |
| Windows에서 Supabase 컨테이너 시작 실패 | Docker Desktop의 WSL2 기반 Linux 컨테이너 엔진 확인 |
| 3000/8000 포트 충돌 | 해당 포트를 사용하는 수동 실행 서버를 종료하고 재실행 |
| 재시작 요청 실패 | 기존 개발 터미널의 오류 확인. 실패한 요청은 종료 코드 1 반환 |
| 실행기에 연결하지 못함 | 기존 개발 터미널 확인 후 종료·재실행. 실행 중인 `.dev/`는 삭제하지 않음 |
| 설치 중 실행기가 켜져 있다는 안내 | 기존 개발 터미널에서 `Ctrl+C`로 종료한 뒤 설치 재시도 |
| 앱이 시작 후 즉시 종료됨 | 해당 앱 로그 확인 후 `npm run dev:frontend` 또는 `npm run dev:backend`로 재시작 |
| DB 상태 API가 503 반환 | 로컬 URL·키·연결 상태와 마이그레이션 적용 여부 확인 |
| 프론트엔드 API 요청 실패 | 백엔드 8000번 포트 및 `NEXT_PUBLIC_API_BASE_URL` 확인 |
| CORS 오류 | 실제 프론트엔드 Origin이 `CORS_ORIGINS`에 포함되는지 확인 |

## `manager.guard` 잠금 파일이 남은 경우

실행기 시작과 비정상 종료 복구를 직렬화하는 동안 `.dev/manager.guard`를 잠깐 사용합니다. 이 구간에서 프로세스가 강제 종료되면 파일이 남을 수 있습니다. 안전하게 복구하려면 해당 파일에 적힌 PID와 기존 개발 터미널을 확인하고, 실행기가 모두 종료된 상태에서 **`.dev/manager.guard`만 삭제**한 뒤 다시 실행하세요. 자동 삭제는 동시에 복구 중인 다른 실행기의 잠금을 지울 수 있어 수행하지 않습니다.

## Windows에서 앱 부모 프로세스가 강제 종료된 경우

Windows 종료는 `taskkill /T`로 실행기 자식의 프로세스 트리를 정리합니다. 앱의 부모 프로세스가 먼저 강제 종료되면 이미 분리된 하위 프로세스를 추적하지 못할 수 있습니다. 재시작 시 포트 충돌이 발생하면 작업 관리자에서 해당 개발 서버의 남은 프로세스를 종료한 뒤 다시 실행하세요. 실행기는 포트만 보고 다른 프로세스를 임의로 종료하지 않습니다.

## macOS/Linux에서 nvm을 현재 셸에 불러오기

새 터미널에서도 nvm을 찾지 못한다면 설치 위치와 셸 설정 파일을 확인합니다. 기본 설치 위치를 사용했다면 다음과 같이 불러올 수 있습니다.

```sh
export NVM_DIR="$HOME/.nvm"
if [ -n "${XDG_CONFIG_HOME:-}" ]; then export NVM_DIR="$XDG_CONFIG_HOME/nvm"; fi
. "$NVM_DIR/nvm.sh"
nvm use
npm run dev
```

사용자 지정 `NVM_DIR`이나 Homebrew nvm을 사용한다면 실제 설치 경로를 지정하세요. 자세한 설치 위치는 [macOS/Linux 설치 안내](setup/macos-linux.md)를 참고하세요.

[문서 목록](../README.md)
