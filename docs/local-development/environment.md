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

## 서버를 개별 실행할 때

공통 실행기를 사용하지 않으면 환경 파일에 값을 직접 설정한다. 백엔드 설정은 `backend/.env.example`, 프론트엔드 설정은 `frontend/.env.example`을 기준으로 작성한다.

- 백엔드에는 로컬 Supabase URL과 서버 전용 키, 허용할 프론트엔드 출처를 설정한다. CLI에서 레거시 키만 제공하면 `service_role` 키를 사용할 수 있다.
- 프론트엔드에는 `NEXT_PUBLIC_API_BASE_URL`을 설정한다. 값을 바꾼 뒤 개발 서버를 다시 실행한다.
- Google SMTP 메일 발송에는 백엔드의 `SMTP_USERNAME`과 `SMTP_PASSWORD`를 설정한다. [이메일 발송 안내](../engineering/email-delivery.md)에서 설정 항목과 호출 방법을 확인한다.
- 로컬 키 확인은 개발자가 자신의 터미널에서 수행하고 출력은 공유하지 않는다. AI 에이전트는 키 조회 명령을 실행하거나 실제 환경 파일을 읽지 않는다.

실행 순서는 [서버 개별 실행](manual-run.md), 스키마 변경 절차는 [코딩과 검증 규칙](../engineering/coding-conventions.md)을 참고한다.

[문서 목록](../README.md)
