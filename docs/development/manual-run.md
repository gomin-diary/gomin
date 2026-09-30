# 서버 개별 실행

일반적인 개발은 저장소 루트에서 `npm run dev`를 사용합니다. 아래는 각 서버를 직접 실행할 때의 안내입니다. 통합 실행기와 함께 사용하면 포트가 충돌하므로 한 가지 방식만 사용하세요.

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

Windows에서 백엔드를 직접 실행할 때는 저장소 루트에서 다음 명령을 사용합니다.

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

[문서 목록](../README.md)
