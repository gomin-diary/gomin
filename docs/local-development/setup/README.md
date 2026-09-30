# 개발 환경 설치

저장소를 내려받은 뒤 루트 디렉터리에서 실행합니다. Node.js가 아직 없어도 시작할 수 있습니다.

```sh
./scripts/setup.cmd
```

| 환경 | 실행할 터미널 | 상세 안내 |
| --- | --- | --- |
| Windows | PowerShell | [Windows 준비 사항](windows.md) |
| macOS | 기본 터미널(zsh 또는 Bash) | [macOS / Linux 준비 사항](macos-linux.md) |
| Linux | Bash | [macOS / Linux 준비 사항](macos-linux.md) |

## 자동으로 준비하는 것

1. Windows에서는 PowerShell, macOS/Linux에서는 Bash 환경설정 스크립트를 호출합니다.
2. 없는 nvm을 설치하고 `.nvmrc`에 지정된 Node.js 24 버전을 설치·선택합니다. macOS/Linux에서는 새 셸의 nvm 기본 버전도 맞춥니다.
3. `npm ci`로 루트 의존성을 설치합니다. 프론트엔드를 선택했다면 프론트엔드 의존성도 설치합니다.
4. 백엔드를 선택했다면 Python 3.12 이상과 실행 중인 Docker를 확인하고, Python 가상환경과 패키지를 준비합니다.
5. 없는 환경 파일만 예제에서 복사합니다. 기존 파일은 유지합니다.

Python 3.12 이상과 Docker는 직접 설치합니다. 운영체제별 문서의 준비 사항을 확인하세요. Supabase CLI는 프로젝트 의존성으로 설치되므로 전역 설치나 Supabase 계정 로그인은 필요하지 않습니다.

설치 명령은 서버를 시작하지 않습니다. 완료 후 **새 터미널**에서 저장소 루트로 이동해 실행합니다. 설치 중 변경한 PATH를 기존 터미널에 직접 반영할 수 없기 때문입니다.

```sh
npm run dev
```

백엔드를 포함해 실행하면 Node 실행기가 로컬 Supabase를 시작하고 마이그레이션을 적용한 뒤 앱 서버를 시작합니다. 첫 실행은 컨테이너 다운로드로 시간이 걸릴 수 있습니다.

## 필요한 대상만 설치

```sh
./scripts/setup.cmd frontend
./scripts/setup.cmd backend
./scripts/setup.cmd all
```

기본값은 `all`입니다. `frontend`는 Python·Docker 없이 설치할 수 있습니다. 백엔드도 공통 실행기가 Node 기반이므로 nvm·Node.js를 설치합니다. 설치한 대상에 맞게 `npm run dev:frontend` 또는 `npm run dev:backend`로 실행하세요.

## 다시 설치

의존성이나 잠금 파일을 변경했다면 개발 실행기를 `Ctrl+C`로 종료하고 같은 설치 명령을 다시 실행합니다. npm 의존성은 잠금 파일 기준으로 다시 설치하며, Python 가상환경은 재사용합니다. 실행 중인 개발 관리자가 있으면 설치를 중단합니다.

기존 `bash scripts/dev.sh`와 `.\scripts\dev.ps1`은 공통 설치 흐름으로 연결됩니다. 이 명령들도 이제 설치만 수행합니다. 실행은 `npm run dev`를 사용하세요.

`./scripts/setup.cmd --help`로 사용법을 확인할 수 있습니다. 설치 중 오류가 발생하면 원인을 해결하고 같은 명령을 다시 실행하세요.

[문서 목록](../../README.md)
