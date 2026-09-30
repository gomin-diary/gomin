# 개발 규칙

- 전역 클라이언트 UI 상태는 `src/stores/`에 정의하고 `useUiStore`로 접근합니다. 루트 Provider가 스토어를 생성해 서버 요청 간 상태가 공유되지 않게 합니다. 메뉴 열림 상태를 사용 예제로 포함했습니다.
- Server Component에서는 Zustand 상태를 읽거나 변경하지 않습니다. API 응답을 무조건 전역 스토어에 저장하지 않습니다.
- 프론트엔드의 API 호출은 `apiFetch("/api/v1/...")`를 이용합니다. 홈 화면은 API를 자동 호출하지 않습니다.
- 백엔드의 DB 작업은 `get_supabase`를 FastAPI 의존성으로 주입하고 `await supabase.table("테이블").select("*").execute()` 형태로 수행합니다. 여러 HTTP 요청은 하나의 트랜잭션이 아니므로 원자적 변경에는 DB 함수와 RPC를 사용합니다. 공유 서버 클라이언트에서는 사용자 로그인이나 세션 변경을 하지 않습니다.
- 서버 Secret 키는 RLS를 우회하므로 업무 API에서 사용자 권한 검사가 필요합니다. 로컬 설정은 테이블 자동 공개를 비활성화했으므로 Data API로 사용할 테이블에는 필요한 `service_role` 권한을 마이그레이션에서 부여합니다.
- DB 변경은 저장소 루트에서 `npm run db:migration:new -- 이름`으로 SQL 파일을 생성한 뒤 작성하고, `npm run db:migrate`로 로컬 DB에 적용합니다. 업무 테이블은 아직 만들지 않았습니다.
- 로컬 Supabase Auth와 Storage는 제공되지만 애플리케이션의 로그인·파일 처리 기능은 아직 구현하지 않았습니다. Upstash 연동과 클라우드 배포도 이번 초기 구성에 포함하지 않았습니다.

[문서 목록](../README.md)
