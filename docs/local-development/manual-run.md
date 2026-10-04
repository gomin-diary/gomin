# 서버 개별 실행

일반적인 개발은 저장소 루트에서 `npm run dev`를 사용합니다. 아래는 각 서버를 직접 실행할 때의 안내입니다. 통합 실행기와 함께 사용하면 포트가 충돌하므로 한 가지 방식만 사용하세요.

## 1. 로컬 Supabase

Docker Desktop 또는 OrbStack을 먼저 실행한 후, 저장소 루트에서 실행합니다.

```bash
npm run supabase:start
```

첫 실행은 컨테이너 이미지 다운로드로 시간이 걸릴 수 있습니다. `supabase/config.toml`이 이미 있으므로 `supabase init`을 다시 실행할 필요는 없습니다. DB가 준비된 후 백엔드를 실행합니다.

서비스 주소와 수동 실행에 필요한 환경변수는 [환경변수와 로컬 서비스](environment.md)를 참고하세요. 설정을 마친 뒤 각 서버를 실행합니다.

기존 로컬 DB를 사용 중이면 저장소 루트에서 `npm run db:migrate`로 미적용 마이그레이션을 적용합니다. 처음 Supabase를 시작하면 마이그레이션이 자동 적용됩니다. DB 변경 절차는 [Supabase 마이그레이션 관리](../engineering/database-migrations.md)를 따릅니다.

## 2. 백엔드 — 별도 터미널

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

## 3. 프론트엔드 — 별도 터미널

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
