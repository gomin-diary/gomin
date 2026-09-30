# 코딩과 검증 규칙

## 프론트엔드

- 전역 UI 상태는 `frontend/src/stores/`에 정의하고 `useUiStore`로 접근한다. 루트 Provider에서 스토어를 생성해 서버 요청 간 상태가 공유되지 않게 한다.
- Server Component에서는 Zustand 상태를 읽거나 변경하지 않는다. API 응답을 무조건 전역 스토어에 저장하지 않는다.
- 백엔드 호출은 `apiFetch("/api/v1/...")`를 사용한다.

## 백엔드

- DB 작업은 `get_supabase`를 FastAPI 의존성으로 주입하고 비동기 Supabase SDK로 수행한다.
- 여러 HTTP 요청은 하나의 트랜잭션이 아니므로 원자적 변경에는 DB 함수와 RPC를 사용한다.
- 공유 서버 클라이언트에서는 사용자 로그인이나 세션 변경을 하지 않는다.
- 서버 전용 키를 사용하는 업무 API에서는 사용자 권한을 검사한다. 서버 키를 프론트엔드에 전달하지 않는다.

## 데이터베이스 변경

DB 변경은 `supabase/migrations/`의 SQL 파일로 관리한다. 저장소 루트에서 마이그레이션을 생성한 뒤 SQL을 작성하고 로컬 DB에 적용한다.

```sh
npm run db:migration:new -- 이름
npm run db:migrate
```

Data API로 사용할 테이블에는 필요한 `service_role` 권한을 마이그레이션에서 부여한다. 여러 환경에 적용할 변경을 로컬 DB에서만 수동으로 수정하지 않는다.

## 변경 검증

명령은 저장소 루트에서 실행한다. 변경한 범위에 맞는 검사를 수행하고, 실제로 확인한 결과와 확인하지 못한 부분을 구분해 기록한다.

| 변경 범위 | 검증 방법 | 확인 범위 |
| --- | --- | --- |
| 프론트엔드 코드 | `npm --prefix frontend run lint`와 `npm --prefix frontend run typecheck` | 코드 규칙과 타입 오류 |
| 프론트엔드 빌드·의존성·설정 | `npm --prefix frontend run build` | 프로덕션 빌드 가능 여부 |
| 설치·실행 스크립트 | `npm test` | 모의 CLI와 임시 프로젝트를 이용한 회귀 테스트 |
| 백엔드 API | 개발 서버에서 변경한 API의 정상·실패 응답 확인 | 실제 요청 처리 동작 |
| DB 연결·마이그레이션 | 로컬 DB에 적용 후 관련 조회·변경과 `/api/v1/health/db` 응답 확인 | 변경 동작과 DB 연결 |
| 문서 | 관련 코드 대조, 상대 링크와 안내 경로 확인 | 설명과 구현의 일치 여부 |

`npm test`는 실제 Docker·Supabase·앱 서버의 통합 동작을 검증하지 않는다. DB 상태 API는 연결 확인용이며 업무 데이터 검증을 대신하지 않는다. Windows 전용 테스트는 Windows 환경에서 확인한다.

## 커밋과 작업 관리

- 커밋은 [커밋 메시지 작성 규칙](commit-messages.md)에 따라 `<type>: <메시지>` 형식으로 작성한다.
- 작업 범위와 완료 기준은 [Jira 이슈 작성 기준](jira-issue-guide.md)을 따른다.

[문서 목록](../README.md)
