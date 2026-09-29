# Gomin

Next.js 프론트엔드와 FastAPI 백엔드의 개발 환경입니다. PostgreSQL은 로컬 Supabase로 실행합니다.

## 폴더 구성

```text
frontend/               Next.js · TypeScript · App Router · Zustand
  src/app/              페이지와 루트 레이아웃
  src/providers/        앱 전역 Zustand Provider
  src/stores/           클라이언트 UI 상태
  src/lib/api.ts        백엔드 요청 함수
backend/                FastAPI · Uvicorn · Psycopg
  app/config.py         환경 변수
  app/database.py       PostgreSQL 연결 풀과 의존성
  app/main.py           앱 수명주기와 기본 API
supabase/               로컬 Supabase 설정과 DB 마이그레이션
```

## 준비 사항

- Node.js 24와 npm (`.nvmrc` 제공)
- Python 3.12
- 실행 중인 Docker 호환 환경: Docker Desktop 또는 OrbStack

아래 명령은 macOS/Linux 터미널 기준입니다. OrbStack을 사용하는 경우 앱을 실행하고 Docker CLI 연동을 활성화해 터미널에서 `docker` 명령을 사용할 수 있게 해주세요. Supabase CLI는 프로젝트 의존성으로 설치되므로 전역 설치나 Supabase 계정 로그인이 필요하지 않습니다.

## 최초 설치

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

## 개발 실행

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

접속 정보는 `npm run supabase:status`로 확인할 수 있습니다. 위 DB 자격 증명은 로컬 개발 전용입니다. 현재 Python API는 PostgreSQL에 직접 연결하므로 Supabase API 키를 복사할 필요가 없습니다.

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

`backend/.env`를 자동으로 읽습니다. 시작할 때 DB 연결 풀이 준비되지 않으면 실행이 실패하므로 Supabase를 먼저 시작하세요. 종료 시 연결 풀을 닫습니다.

### 3. 프론트엔드 — 별도 터미널

저장소 루트에서 실행합니다.

```bash
npm --prefix frontend run dev
```

웹: http://127.0.0.1:3000

`frontend/.env.local`의 `NEXT_PUBLIC_API_BASE_URL`로 API 주소를 지정합니다. 이 변수는 브라우저에 공개되므로 비밀 키를 넣지 않습니다. 값 변경 후에는 개발 서버를 다시 실행합니다.

## 개발 규칙

- 전역 클라이언트 UI 상태는 `src/stores/`에 정의하고 `useUiStore`로 접근합니다. 루트 Provider가 스토어를 생성해 서버 요청 간 상태가 공유되지 않게 합니다. 메뉴 열림 상태를 사용 예제로 포함했습니다.
- Server Component에서는 Zustand 상태를 읽거나 변경하지 않습니다. API 응답을 무조건 전역 스토어에 저장하지 않습니다.
- 프론트엔드의 API 호출은 `apiFetch("/api/v1/...")`를 이용합니다. 홈 화면은 API를 자동 호출하지 않습니다.
- 백엔드의 DB 작업은 `get_connection`을 FastAPI 의존성으로 주입해 사용합니다. 연결 컨텍스트가 정상 종료되면 커밋하고 예외가 발생하면 롤백합니다.
- DB 변경은 저장소 루트에서 `npm run db:migration:new -- 이름`으로 SQL 파일을 생성한 뒤 작성하고, `npm run db:migrate`로 로컬 DB에 적용합니다. 업무 테이블은 아직 만들지 않았습니다.
- 로컬 Supabase Auth와 Storage는 제공되지만 애플리케이션의 로그인·파일 처리 기능은 아직 구현하지 않았습니다. Upstash 연동과 클라우드 배포도 이번 초기 구성에 포함하지 않았습니다.

## 종료 및 문제 해결

프론트엔드와 백엔드는 각 터미널에서 `Ctrl+C`로 종료합니다. Supabase는 저장소 루트에서 중지합니다.

```bash
npm run supabase:stop
```

일반 중지는 로컬 데이터를 보존합니다. 데이터가 필요한 경우 `--no-backup` 옵션이나 Docker 볼륨 삭제를 사용하지 마세요.

| 증상 | 확인 사항 |
| --- | --- |
| Docker 명령/데몬을 찾지 못함 | Docker Desktop 또는 OrbStack 실행, Docker CLI의 PATH 설정 |
| PostgreSQL 연결 실패 | Supabase 시작 완료 여부, `backend/.env`의 54322 포트 |
| 프론트엔드 API 요청 실패 | 백엔드 실행 여부, `NEXT_PUBLIC_API_BASE_URL` |
| CORS 오류 | `CORS_ORIGINS`의 JSON 배열에 실제 프론트엔드 Origin 추가 |
| 포트 충돌 | 3000, 8000, 54320~54324 점유 확인; 변경 시 환경 변수도 함께 수정 |

요청에 따라 이번 구성 과정에서 테스트, 린트, 타입 검사, 빌드 및 서버 실행 검증은 수행하지 않았습니다.

구성 참고: [Next.js 설치](https://nextjs.org/docs/app/getting-started/installation), [Zustand와 Next.js](https://zustand.docs.pmnd.rs/learn/guides/nextjs), [FastAPI 환경 설정](https://fastapi.tiangolo.com/advanced/settings/), [로컬 Supabase](https://supabase.com/docs/guides/local-development/cli/getting-started).
