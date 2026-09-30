# 환경변수와 로컬 서비스

설치 스크립트는 파일이 없을 때만 `frontend/.env.example`을 `.env.local`로, `backend/.env.example`을 `.env`로 복사합니다.

공통 실행기는 로컬 개발 전용입니다. 다음 값을 자식 프로세스의 환경변수로 전달하므로 기존 파일이나 클라우드 설정을 덮어쓰지 않습니다.

| 대상 | 환경변수 | 공통 실행기에서 사용하는 값 |
| --- | --- | --- |
| 프론트엔드 | `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` |
| 백엔드 | `SUPABASE_URL` | 로컬 Supabase CLI에서 조회한 루프백 URL |
| 백엔드 | `SUPABASE_SECRET_KEY` | 로컬 Secret 키 또는 service_role 키 |
| 백엔드 | `CORS_ORIGINS` | `["http://127.0.0.1:3000","http://localhost:3000"]` |

키를 직접 복사할 필요가 없습니다. `NEXT_PUBLIC_` 변수는 브라우저에 공개되므로 서버 Secret 키를 넣지 않습니다. 앱을 직접 실행하거나 클라우드에 배포할 때는 해당 환경의 값을 따로 설정합니다.

## 주소

| 서비스 | 주소 |
| --- | --- |
| 웹 | http://127.0.0.1:3000 |
| API 문서 | http://127.0.0.1:8000/docs |
| Supabase API / Storage | http://127.0.0.1:54321 |
| Supabase Studio | http://127.0.0.1:54323 |
| 로컬 이메일 수신함 | http://127.0.0.1:54324 |
| PostgreSQL 17 | `postgresql://postgres:postgres@127.0.0.1:54322/postgres` |

PostgreSQL 주소는 DB 관리 도구용입니다. 앱은 Supabase Data API로 연결합니다. 백엔드 상태 API는 `GET /api/v1/health`, DB 연결 확인은 `GET /api/v1/health/db`입니다.

## 데이터베이스 변경

```sh
npm run db:migration:new -- 이름
npm run db:migrate
```

생성된 SQL 파일을 작성한 뒤 로컬 DB에 적용합니다. 공통 실행기도 백엔드 시작 시 미적용 마이그레이션을 적용합니다. Supabase 상태 조회는 `npm run supabase:status`를 사용합니다. 이 명령의 출력에는 키가 포함되므로 공유할 때 주의하세요.

[문서 목록](../README.md)
