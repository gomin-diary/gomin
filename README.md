# Gomin

Next.js 프론트엔드와 FastAPI 백엔드의 개발 환경입니다. PostgreSQL은 로컬 Supabase로 실행합니다.

## 폴더 구성

```text
frontend/               Next.js · TypeScript · App Router · Zustand
  src/app/              페이지와 루트 레이아웃
  src/providers/        앱 전역 Zustand Provider
  src/stores/           클라이언트 UI 상태
  src/lib/api.ts        백엔드 요청 함수
backend/                FastAPI · Uvicorn · Supabase Python SDK
  app/config.py         환경 변수
  app/database.py       Supabase API 클라이언트와 의존성
  app/main.py           앱 수명주기와 기본 API
supabase/               로컬 Supabase 설정과 DB 마이그레이션
scripts/dev.sh          필수 도구 확인과 의존성 설치
scripts/dev.py          로컬 키 자동 연결과 개발 서버 실행·종료
scripts/restart.sh      frontend / backend / all 선택 실행·재실행
```

## 준비 사항

- nvm (Node.js 24와 npm은 스크립트가 설치, `.nvmrc` 기준)
- Python 3.12
- 실행 중인 Docker 호환 환경: Docker Desktop 또는 OrbStack

macOS/Linux에서는 Bash, Windows에서는 PowerShell에서 WSL2를 통해 실행합니다. OrbStack을 사용하는 경우 앱을 실행하고 Docker CLI 연동을 활성화해 터미널에서 `docker` 명령을 사용할 수 있게 해주세요. Supabase CLI는 프로젝트 의존성으로 설치되므로 전역 설치나 Supabase 계정 로그인이 필요하지 않습니다.

## 한 번에 설치하고 실행

### macOS / Linux

저장소 루트에서 다음 명령을 실행합니다. 다른 디렉터리에서는 `dev.sh`의 경로를 지정해도 됩니다.

```bash
bash scripts/dev.sh
```

### Windows PowerShell (WSL2)

현재 스크립트는 Bash와 Unix 프로세스 제어를 사용합니다. Windows에서는 **PowerShell에서 WSL2를 호출**합니다. Windows 네이티브 Python이나 nvm-windows로 실행하는 방식은 지원하지 않습니다.

WSL이 없다면 관리자 권한 PowerShell에서 설치합니다.

```powershell
wsl --install -d Ubuntu-26.04
```

설치 안내에 따라 Windows를 재시작하고 Ubuntu의 사용자 계정을 생성하세요. Docker Desktop을 실행한 후 **Settings → Resources → WSL Integration**에서 해당 배포판을 활성화합니다. [WSL 설치·명령 안내](https://learn.microsoft.com/en-us/windows/wsl/basic-commands), [Docker Desktop WSL 설정](https://docs.docker.com/desktop/features/wsl/)

최초 한 번 Ubuntu 터미널에서 필요한 도구와 nvm을 설치합니다. PowerShell에서 `wsl -d Ubuntu-26.04`로 Ubuntu 터미널에 들어갈 수 있습니다.

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv curl git
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh | bash
```

저장소는 WSL 내부 경로(예: `/home/사용자/gomin`)에 준비하세요. 다른 OS에서 만든 `node_modules`나 `.venv`는 복사하지 않습니다. 아래 명령은 **PowerShell**에서 실행하며, 배포판 이름과 저장소 경로를 실제 값으로 바꿉니다.

```powershell
$Distro = "Ubuntu-24.04"
$ProjectPath = "/home/사용자/gomin"
wsl -d $Distro --cd $ProjectPath --exec bash scripts/dev.sh
```

Windows 브라우저에서 `http://localhost:3000`으로 접속합니다. 설치와 실행은 WSL 안에서 진행되므로 Windows에 Node.js나 Python을 별도로 설치할 필요가 없습니다. WSL에 nvm이 없으면 스크립트가 curl 설치 방법을 안내합니다.

### 공통 실행 동작

스크립트가 다음 순서로 처리합니다.

1. nvm, Python 3.12, Docker 실행 상태 확인
2. Node.js 선택 및 프론트엔드·백엔드 의존성 설치
3. 없는 환경 파일만 예제에서 생성
4. 로컬 Supabase 시작 및 미적용 마이그레이션 적용
5. 로컬 API URL·Secret 키 자동 조회
6. 프론트엔드(3000)와 백엔드(8000) 동시 실행

키를 직접 복사할 필요가 없습니다. 로컬 Supabase URL·키·CORS는 백엔드 프로세스의 환경 변수로 전달하며, 프론트엔드 API 주소도 로컬 백엔드로 지정합니다. 기존 `.env` 파일이나 클라우드 설정은 덮어쓰지 않습니다. 이 스크립트는 **로컬 개발 전용**입니다.

실행할 때마다 잠금 파일 기준으로 의존성을 설치합니다. 첫 실행은 Node.js·Python 패키지·컨테이너 이미지 다운로드로 시간이 걸릴 수 있습니다. 테스트나 빌드는 실행하지 않습니다.

`Ctrl+C`를 누르면 관리 중인 앱 서버와 하위 프로세스를 정리합니다. 서버 하나가 종료되어도 다른 서버와 개발 관리자는 유지됩니다. Supabase는 다음 실행을 위해 유지하며, 중지하려면 `npm run supabase:stop`을 실행합니다. nvm이 이미 로드된 터미널에서는 `npm run dev`도 사용할 수 있습니다.

### 대상별 실행 / 재실행

최초 설치 이후에는 아래 스크립트를 사용합니다. 실행 중인 대상이 없으면 시작하고, 있으면 해당 프로세스와 하위 프로세스를 종료한 다음 새로 시작합니다.

```bash
bash scripts/restart.sh frontend
bash scripts/restart.sh backend
bash scripts/restart.sh all
```

Windows PowerShell에서는 같은 WSL 배포판과 저장소 경로를 지정하고, 원하는 대상의 명령 하나를 실행합니다.

```powershell
$Distro = "Ubuntu-24.04"
$ProjectPath = "/home/사용자/gomin"
wsl -d $Distro --cd $ProjectPath --exec bash scripts/restart.sh frontend
wsl -d $Distro --cd $ProjectPath --exec bash scripts/restart.sh backend
wsl -d $Distro --cd $ProjectPath --exec bash scripts/restart.sh all
```

| 대상 | 동작 |
| --- | --- |
| `frontend` | 프론트엔드만 실행·재실행, 백엔드 유지 |
| `backend` | 백엔드만 실행·재실행, 프론트엔드 유지 |
| `all` | 프론트엔드와 백엔드 모두 실행·재실행 |

- `dev.sh`와 `restart.sh`가 같은 개발 관리자를 사용합니다. 기존 개발 터미널이 있다면 **다른 터미널**에서 재실행 명령을 입력하세요. 처리 결과를 출력한 뒤 명령이 끝나며 서버 로그는 기존 개발 터미널에 표시됩니다.
- 실행 중인 관리자가 없으면 호출한 터미널이 개발 터미널이 됩니다. 해당 터미널의 `Ctrl+C`는 관리 중인 모든 앱 서버를 종료합니다.
- 의존성을 다시 설치하지 않습니다. 패키지를 변경했다면 기존 개발 터미널에서 종료한 후 `bash scripts/dev.sh`를 실행하세요.
- 프론트엔드만 실행할 때는 Docker나 Supabase가 필요하지 않습니다. 백엔드가 포함되면 로컬 Supabase를 준비하고 마이그레이션을 적용하지만, 이미 실행 중인 Supabase를 재시작하지는 않습니다. `all`의 대상도 두 앱 서버입니다.
- 관리자가 직접 실행한 프로세스만 종료합니다. 수동으로 실행한 서버나 다른 프로그램이 3000/8000 포트를 사용 중이면 직접 종료하라는 안내를 표시합니다.
- 관리용 잠금 파일과 소켓은 Git에서 제외한 `.dev/`에 저장합니다. 실행 중에는 이 폴더를 삭제하지 마세요.

npm을 사용할 수 있는 터미널에서는 `npm run dev:frontend`, `npm run dev:backend`, `npm run dev:all`도 같은 동작을 수행합니다.

### nvm이 없는 경우

스크립트가 설치 명령을 안내하고 종료합니다. 아래 **두 방법 중 하나**로 설치한 뒤 `bash scripts/dev.sh`를 다시 실행하세요. 사용자 셸 설정은 스크립트가 자동 변경하지 않습니다.

**curl — macOS / Linux**

```bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
```

`XDG_CONFIG_HOME`을 사용한다면 설치 경로가 `$XDG_CONFIG_HOME/nvm`일 수 있습니다. 설치 프로그램이 안내한 `NVM_DIR`을 사용하세요. [nvm 공식 설치 안내](https://github.com/nvm-sh/nvm)

**Homebrew — macOS**

[Homebrew](https://brew.sh)가 설치되어 있어야 합니다.

```bash
brew install nvm
mkdir -p "$HOME/.nvm"
export NVM_DIR="$HOME/.nvm"
. "$(brew --prefix nvm)/nvm.sh"
```

마지막 두 줄을 `~/.zshrc`에 추가하면 새 터미널에서도 적용됩니다. 스크립트는 표준 nvm 경로와 Homebrew 설치 경로를 모두 확인합니다. [Homebrew nvm 안내](https://formulae.brew.sh/formula/nvm)

Python이 없다면 macOS에서 `brew install python@3.12`로 설치합니다. Linux에서는 Python 3.12와 venv 지원을 준비하세요. 별도 경로를 사용하면 `PYTHON_BIN=/경로/python3.12 bash scripts/dev.sh`로 지정할 수 있습니다. 기존 `backend/.venv`가 있으면 해당 가상환경을 우선 사용합니다.

## 수동 설치 (개별 실행이 필요한 경우)

Windows에서는 아래 Bash 명령을 WSL 터미널에서 실행합니다.

저장소 루트에서 실행합니다. nvm을 사용하지 않는 경우 Node.js 24를 별도로 준비하고 nvm 명령은 생략합니다.

```bash
nvm install
nvm use
npm ci
npm --prefix frontend ci
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env
```

환경 파일 복사는 최초 한 번만 수행합니다. 이미 설정한 파일이 있으면 덮어쓰지 마세요. `requirements.in`은 직접 의존성 범위, `requirements.txt`는 설치 버전을 고정한 파일입니다. npm 의존성은 각 `package-lock.json`으로 고정합니다.

## 수동 개발 실행

### 1. 로컬 Supabase

Docker Desktop 또는 OrbStack을 먼저 실행한 후, 저장소 루트에서 실행합니다.

```bash
npm run supabase:start
```

첫 실행은 컨테이너 이미지 다운로드로 시간이 걸릴 수 있습니다. `supabase/config.toml`이 이미 있으므로 `supabase init`을 다시 실행할 필요는 없습니다. DB가 준비된 후 백엔드를 실행합니다.

| 서비스 | 로컬 주소 |
| --- | --- |
| PostgreSQL 17 | `postgresql://postgres:postgres@127.0.0.1:54322/postgres` |
| Supabase API / Storage | http://127.0.0.1:54321 |
| Supabase Studio | http://127.0.0.1:54323 |
| 로컬 이메일 수신함 | http://127.0.0.1:54324 |

`npm run supabase:status`에서 API URL과 **Secret** 키를 확인해 `backend/.env`에 입력합니다. CLI에 레거시 키만 표시되면 `service_role` 키를 같은 변수에 입력할 수 있습니다. 위 PostgreSQL 주소는 DB 관리 도구용이며 애플리케이션 연결에는 사용하지 않습니다.

```dotenv
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SECRET_KEY=<로컬 Supabase의 Secret 키>
CORS_ORIGINS=["http://127.0.0.1:3000","http://localhost:3000"]
```

기존 로컬 DB를 사용 중이면 저장소 루트에서 `npm run db:migrate`로 상태 확인용 DB 함수를 추가합니다. 처음 Supabase를 시작하면 마이그레이션이 자동 적용됩니다.

### 2. 백엔드 — 별도 터미널

저장소 루트에서 시작합니다.

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API 문서: http://127.0.0.1:8000/docs
- 기본 상태 API: `GET /api/v1/health`
- DB 상태 API: `GET /api/v1/health/db`

`backend/.env`를 자동으로 읽습니다. URL 또는 키가 비어 있으면 시작할 수 없습니다. 시작 시에는 HTTP 클라이언트를 생성하고, 실제 연결과 키 인증은 요청 시 수행합니다. DB 상태 API는 `health_check` 함수를 Data API로 호출하며 잘못된 키·연결 실패·미적용 마이그레이션은 503으로 응답합니다. 종료 시 HTTP 연결을 닫습니다.

### 3. 프론트엔드 — 별도 터미널

저장소 루트에서 실행합니다.

```bash
npm --prefix frontend run dev
```

웹: http://127.0.0.1:3000

`frontend/.env.local`의 `NEXT_PUBLIC_API_BASE_URL`로 API 주소를 지정합니다. 이 변수는 브라우저에 공개되므로 비밀 키를 넣지 않습니다. 값 변경 후에는 개발 서버를 다시 실행합니다.

## 배포 환경 — Render + Supabase Cloud

Render의 Environment에 다음 값을 등록합니다. 프로젝트 URL과 Secret 키는 해당 Supabase Cloud 프로젝트의 Connect/API Keys 화면에서 확인합니다.

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY=<Supabase Cloud의 Secret 키>
CORS_ORIGINS=["https://<프론트엔드 도메인>"]
```

DB 비밀번호나 `DATABASE_URL`은 백엔드 실행에 필요하지 않습니다. Secret 키는 서버 전용이며 프론트엔드 환경 변수에 넣지 않습니다. 이 키는 Supabase 계정용 Personal Access Token과 다릅니다.

Render의 Root Directory는 `backend`, Build Command는 `pip install -r requirements.txt`, Start Command는 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`로 지정합니다. Python 3.12를 사용합니다.

Supabase Cloud에서 Data API를 활성화하고 `public` 스키마를 노출해야 합니다. 배포 전 `supabase/migrations/`의 SQL을 해당 프로젝트에 적용합니다. 현재 상태 확인 함수는 Supabase SQL Editor에서 `20260929000000_health_check.sql` 내용을 실행하면 추가할 수 있습니다. 애플리케이션은 시작할 때 스키마를 변경하지 않습니다.

## 개발 규칙

- 전역 클라이언트 UI 상태는 `src/stores/`에 정의하고 `useUiStore`로 접근합니다. 루트 Provider가 스토어를 생성해 서버 요청 간 상태가 공유되지 않게 합니다. 메뉴 열림 상태를 사용 예제로 포함했습니다.
- Server Component에서는 Zustand 상태를 읽거나 변경하지 않습니다. API 응답을 무조건 전역 스토어에 저장하지 않습니다.
- 프론트엔드의 API 호출은 `apiFetch("/api/v1/...")`를 이용합니다. 홈 화면은 API를 자동 호출하지 않습니다.
- 백엔드의 DB 작업은 `get_supabase`를 FastAPI 의존성으로 주입하고 `await supabase.table("테이블").select("*").execute()` 형태로 수행합니다. 여러 HTTP 요청은 하나의 트랜잭션이 아니므로 원자적 변경에는 DB 함수와 RPC를 사용합니다. 공유 서버 클라이언트에서는 사용자 로그인이나 세션 변경을 하지 않습니다.
- 서버 Secret 키는 RLS를 우회하므로 업무 API에서 사용자 권한 검사가 필요합니다. 로컬 설정은 테이블 자동 공개를 비활성화했으므로 Data API로 사용할 테이블에는 필요한 `service_role` 권한을 마이그레이션에서 부여합니다.
- DB 변경은 저장소 루트에서 `npm run db:migration:new -- 이름`으로 SQL 파일을 생성한 뒤 작성하고, `npm run db:migrate`로 로컬 DB에 적용합니다. 업무 테이블은 아직 만들지 않았습니다.
- 로컬 Supabase Auth와 Storage는 제공되지만 애플리케이션의 로그인·파일 처리 기능은 아직 구현하지 않았습니다. Upstash 연동과 클라우드 배포도 이번 초기 구성에 포함하지 않았습니다.

## 종료 및 문제 해결

통합 스크립트는 `Ctrl+C` 한 번으로 두 앱 서버를 종료합니다. 수동 실행했다면 각 터미널에서 종료합니다. Supabase는 저장소 루트에서 중지합니다.

```bash
npm run supabase:stop
```

일반 중지는 로컬 데이터를 보존합니다. 데이터가 필요한 경우 `--no-backup` 옵션이나 Docker 볼륨 삭제를 사용하지 마세요.

| 증상 | 확인 사항 |
| --- | --- |
| Docker 명령/데몬을 찾지 못함 | Docker Desktop 또는 OrbStack 실행, Docker CLI의 PATH 설정 |
| PowerShell에서 WSL 실행 실패 | `wsl -l -v`로 배포판 이름과 버전 2 확인, `$ProjectPath`에 WSL 내부 경로 지정 |
| WSL에서 Docker 연결 실패 | Docker Desktop의 WSL Integration에서 사용 중인 배포판 활성화 |
| Supabase 연결 실패 | 로컬 API의 54321 포트, `SUPABASE_URL`, 서버 키, 마이그레이션 적용 여부 |
| 프론트엔드 API 요청 실패 | 백엔드 실행 여부, `NEXT_PUBLIC_API_BASE_URL` |
| CORS 오류 | `CORS_ORIGINS`의 JSON 배열에 실제 프론트엔드 Origin 추가 |
| 포트 충돌 | 3000, 8000, 54320~54324 점유 확인; 변경 시 환경 변수도 함께 수정 |

요청에 따라 이번 구성 과정에서 테스트, 린트, 타입 검사, 빌드 및 서버 실행 검증은 수행하지 않았습니다.

구성 참고: [Next.js 설치](https://nextjs.org/docs/app/getting-started/installation), [Zustand와 Next.js](https://zustand.docs.pmnd.rs/learn/guides/nextjs), [FastAPI 환경 설정](https://fastapi.tiangolo.com/advanced/settings/), [로컬 Supabase](https://supabase.com/docs/guides/local-development/cli/getting-started).
