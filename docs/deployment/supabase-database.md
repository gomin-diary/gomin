# Supabase — 데이터베이스

Supabase Cloud의 PostgreSQL과 Data API를 운영한다. FastAPI는 비동기 Supabase SDK와 서버 전용 키로 Data API를 호출하며, 회원 인증은 FastAPI에서 처리한다.

## 프로젝트와 연결 설정

Supabase 프로젝트에서 Data API를 활성화하고 `public` 스키마를 노출한다. 업무 테이블의 RLS와 `service_role` 권한은 저장소의 마이그레이션으로 관리한다.

Render 백엔드에는 다음 설정을 등록한다. 설정 이름은 `backend/.env.example`을 기준으로 한다.

| 설정 | 용도 |
| --- | --- |
| `SUPABASE_URL` | 대상 Supabase Cloud 프로젝트의 API 주소 |
| `SUPABASE_SECRET_KEY` | 백엔드가 Data API와 Storage에 사용하는 서버 전용 키 |

백엔드는 DB 비밀번호로 직접 연결하지 않으며 `DATABASE_URL`을 요구하지 않는다. 서버 전용 키를 프론트엔드나 `NEXT_PUBLIC_` 변수에 넣지 않는다.

## 마이그레이션 배포

SQL 작성·로컬과 PR 검증·운영 Secrets 등록·실패 처리는 [Supabase 마이그레이션 관리](../engineering/database-migrations.md)를 따른다.

운영 적용은 `main`에서 [Supabase production migrations](../../.github/workflows/supabase-migrations-production.yml)를 수동 실행한다. 워크플로가 대상 프로젝트에 연결하고 미적용 SQL을 확인한 뒤 적용한다. 성공 후 관련 스키마·권한·API 동작을 확인하고 Render 백엔드를 배포한다. 애플리케이션은 시작할 때 운영 스키마를 변경하지 않는다.

마이그레이션용 GitHub Environment `supabase-production`의 `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD`, `SUPABASE_PROJECT_ID`는 Render의 런타임 설정과 별도로 관리한다. Personal Access Token과 백엔드의 `SUPABASE_SECRET_KEY`는 서로 다른 자격증명이다. 실제 값은 문서에 기록하지 않는다.

로컬 테스트 계정인 `supabase/seed.sql`은 운영에 적용하지 않는다. 마이그레이션 실패 시 앱 배포를 중단하고 적용 이력과 실제 스키마를 먼저 확인한다.

## 운영 확인

`GET /api/v1/health/db`가 HTTP 200과 `data.database: "connected"`를 반환하는지 확인한다. 이 API는 [상태 라우터](../../backend/app/api/routes/health.py)가 `health_check` DB 함수를 호출해 연결을 검사한다. 연결·함수 호출이 실패하거나 결과가 `true`가 아니면 HTTP 503을 반환한다.

이 결과는 업무 테이블 전체, Storage 업로드, 메일 발송을 검증하지 않는다. 배포한 기능의 조회·변경·권한 동작도 별도로 확인한다.

DB 상태 확인이 실패하면 대상 프로젝트·Data API·서버 키 설정과 마이그레이션 적용 이력을 확인한다. 키 조회 결과나 실제 사용자 데이터를 로그·채팅에 출력하지 않는다.

[Storage 운영](supabase-storage.md) · [배포·운영 개요](README.md) · [문서 목록](../README.md)
