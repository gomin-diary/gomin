# 털어놓기 MVP 검증 기록

검증일: 2026-10-08~09(Asia/Seoul). 개발 GOMIN-69, QA GOMIN-70. 기준: [GOMIN-71 최신 최종 명세](https://younkim.atlassian.net/browse/GOMIN-71), 수정 시각 2026-10-08 12:23:18 +09:00. 작업 브랜치: `codex/gomin-69-talk-mvp`.

## 실행 결과와 범위

| 검사 | 결과 | 실제 확인 범위 |
| --- | --- | --- |
| frontend lint·typecheck | 통과 | 오류·경고 없음 |
| frontend 단위 검증 | REST 연동 변경 후 관련 14개 통과; 직전 전체 회귀는 50개 중 49개 통과 | 대화 9개·로그인 복귀 5개. 기존 공개 문서 symlink fixture는 Windows EPERM이며 권한을 얻은 재실행도 동일; 이번 관련 변경 후 해당 테스트를 반복하지 않음 |
| frontend 문서 생성·프로덕션 빌드 | 통과 | 공개 문서 55개 생성, 서비스 레이아웃의 대화·후속 전달 경로 포함 빌드 |
| backend unittest | 152개 통과(대화·AI 어댑터 15개 포함) | REST ASGI 요청, main의 실제 클라이언트와 MockTransport, 저장소·제공자 격리, 정상·실패·비소유 요청과 main 회귀 |
| 새 대화 RPC 검증 | 8개 통과 | 임시 PostgreSQL(PGlite)에 전체 SQL 적용; 소유권·권한·순번·버전·시간·lease·확정·기존 식별자 |
| 기존 대화·컬렉션 DB 회귀 검증 | 16개 통과 | 새 SQL·main의 Storage/그림일기 SQL 포함 전체 적용 후 기존 제약 보존 |
| Chrome 브라우저 QA | 4개 크기 통과, 실패·비로그인·확정 ID 후속 전달 통과 | 모의 API의 1440×900, 390×844, 320×568, 667×375 화면. /talk?summary=… 이동·동일 저장 요약 조회·이미지 자동 생성 없음 |
| Figma 확인 | PC·모바일 6개 확인 | Computer Use로 데스크톱 앱의 Conversation·Wrap up·Summary 읽기 |
| 실제 AI 호출 | 미수행 | CodysseyTalkProvider·기존 CodysseyClient·기본 gpt-5.4-mini 설정 연결. MockTransport로 HTTP 요청/출력/오류 검증; 실제 키의 외부 호출과 품질은 미검증 |
| 실제 Supabase 적용 | 로컬 적용·RPC 검증 통과 | 미적용 마이그레이션 12개 적용. 대화 버전 20261008044707·RPC 7개 등록 재조회, service_role에서 저장·타인 거부·대기 제한·시간 복원·재요약·확정·기존 prepare_diary_summary 검증 후 롤백 |
| 실제 Data API·쿠키·AI 통합 | 미수행 | 모의 저장소/제공자와 PGlite의 분리 검증은 실제 Supabase 연동을 대신하지 않음 |
| 배포·운영 DB·실기기 | 미수행 | 배포 주소 검증, 여러 DB 연결의 잠금 경합, Safari·실제 한글 IME·가상 키보드·안전영역 추가 확인 필요 |

브라우저 화면을 직접 검토해 뒤로가기 자산 경로를 수정했다. 작은 화면의 입력창·글자 수·전송·요약 버튼은 화면 안 배치 또는 요약 영역 스크롤로 조작 가능하다. 테스트 전용 응답은 운영 코드의 실제 AI 응답으로 사용하지 않는다. 실제 환경 파일·백업은 읽지 않았다.

PR #45의 main(5f4eec0) 반영 후 사용자 지시에 따라 REST 채팅과 공용 Codyssey 클라이언트 연동을 수정했다. 모의 HTTP 요청에서 이전 맥락·원문 범위·JSON 요약·동일 대화 재요약을 확인하고 제공자 실패/시간 초과/미설정/잘못된 출력을 완료 결과로 저장하지 않는 것을 검증했다. 기존 공개 문서 테스트의 Windows 권한 오류를 전체 테스트 통과로 표시하지 않았다. 최초 DB 연결 거부는 당시 결과이며 이번에는 실제 로컬 DB 적용과 트랜잭션 검증까지 성공했다.

## GOMIN-71 검수 22개

아래의 **통과(격리 검증)**는 명시된 테스트 범위의 확인이다. 실제 서비스 전체 검수가 완료됐다는 뜻이 아니다. 부분 확인 항목은 최종 완료로 표시하지 않는다.

| 번호 | 명세 검수 항목 | 판정 | 근거·남은 확인 |
| --- | --- | --- | --- |
| 1 | 비로그인 제한·로그인 대화 이용 | 통과(격리 검증) | Chrome AuthGuard 리다이렉트, ASGI 모든 경로 401, 모의 로그인 화면 |
| 2 | 다른 회원 대화·요약 조회·전송·확정 차단 | 통과(격리 검증) | backend 세션 회원 전달 및 모든 경로 거부, PGlite 실제 SQL의 비소유 명령 거부 |
| 3 | 빈 입력·공백·줄바꿈 전송 금지 | 통과(격리 검증) | frontend·backend·SQL 경계 검사 |
| 4 | 공백·줄바꿈 포함 100자·101자·글자 수 | 통과(격리 검증) | 세 계층 검사, Chrome 100/100과 버튼 상태, Unicode 코드 포인트 |
| 5 | PC·모바일 Enter·Shift·한글 조합 | 부분 확인 | 단위 분기와 Chrome 합성 composition 이벤트 통과; 실기기 한국어 IME 확인 필요 |
| 6 | 말풍선·시각·순서·이전 맥락 대화 | 부분 확인 | 표시·서버 순서/시각·제공자에 전달한 이전 원문 검증; 실제 AI의 공감·맥락 응답 미검증 |
| 7 | 대기 중 편집·전송 제한·입력 유지·자동 전송 없음 | 통과(격리 검증) | controller와 Chrome 대기 입력·전송 횟수 검사 |
| 8 | 첨부 기능·아이콘 없음 | 통과(격리 검증) | 화면·코드 검사, file input 없음 |
| 9 | 저장 원문·순서·시간 복원·초안 미복원 | 통과(격리 검증) | SQL 시각 불변, controller 복원, Chrome 같은 URL 재접속·초안 비움 |
| 10 | 첫 사용자 저장 전/후 마무리 활성화 | 통과(격리 검증) | 미저장 비활성, 저장 후 AI 대기 중 활성, 다음 접수 중에도 선택 가능 |
| 11 | 같은 대화 저장 원문만 요약·초안 제외 | 부분 확인 | provider 입력 순번 경계·다른 대화 제외·draft 미전달 검증; 실제 AI 생성 미검증 |
| 12 | 문장·목록·태그 세 영역 | 통과(격리 검증) | 구조 검증·Chrome 요약 세 영역·시각 확인 |
| 13 | 같은 대화 재개·추가 내용 새 요약 | 부분 확인 | SQL·controller·Chrome 동일 ID·버전2·원문 범위 검증; 실제 AI 재요약 미검증 |
| 14 | 요약·감정 태그 직접 편집 없음 | 통과(격리 검증) | 표시 전용 요소와 API 입력 계약 검사 |
| 15 | 표시 요약 확정·식별자와 정보 전달 | 통과(격리·로컬 DB 검증) | 최신 요약 확정 RPC, 서버 본문 handoff, 확정 조회·재접속, 기존 그림일기 화면에 확정 ID 전달 |
| 16 | 이미지·컬렉션 성공으로 표시하지 않음 | 통과(격리 검증) | UI 보류 문구, SQL 이미지 job·결과·컬렉션 행 미생성 |
| 17 | 응답·요약 별도 로딩·오류·보류 | 통과(격리 검증) | Chrome 대기·미설정 응답 실패·요약 실패 표시 |
| 18 | 실패 결과를 성공으로 표시하지 않음·재시도/초안 복구 없음 | 통과(격리 검증) | backend invalid/timeout 실패, controller 조회/확정 실패, SQL 실패·늦은 완료, Chrome 재시도/확정 버튼 없음 |
| 19 | PC·모바일 대화·마무리·요약·재개·확정·뒤로가기 | 통과(격리 검증) | 4개 viewport에서 전체 흐름·뒤로가기·주소 전환 검증 |
| 20 | 작은 모바일의 입력·글자 수·요약·버튼 조작 | 부분 확인 | 320×568·667×375 bounding box·스크롤·넘침 통과; 실기기 키보드·Safari·safe area 미검증 |
| 21 | lint·typecheck·backend 정상/실패/소유권·Jira 기록 | 통과(격리 검증) | 위 실행 결과와 GOMIN-69 코멘트 10039·GOMIN-70 코멘트 10040 등록 확인 |
| 22 | 모의·실제 AI·실제 DB·배포 여부 분리 | 통과 | 위 표와 구현 문서에 별도 기록 |

## 재현 가능한 검증

저장소 루트에서 실행한다. 실제 환경 설정 없이 단위·격리 테스트를 실행한다.

```sh
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
```

Windows backend 검증은 UTF-8 모드에서 unittest discover를 사용한다(PYTHONUTF8=1). 이번 회귀는 실제 환경 파일을 제외한 `.dev/talk-pr-project/backend`에 app·tests를 복사하고 seed.sql을 같은 임시 프로젝트에 배치한 뒤, PYTHONPATH를 해당 backend로 지정했다. 기존 `backend/.venv/Scripts/python.exe`를 사용하며 main의 잠금 파일과 같은 Pillow 12.3.0을 설치했다. 격리 환경의 Windows asyncio 제약이 있어 실행 권한을 얻어 검증했다.

DB 테스트는 `PGLITE_MODULE`에 설치된 `@electric-sql/pglite` 모듈의 파일 URL을 지정하고 `node --test supabase/tests/talk-mvp.test.mjs supabase/tests/conversation-collection.test.mjs`로 실행한다. 저장소의 기존 DB 테스트와 같은 임시 PostgreSQL 방식이다. 로컬 개발 DB 데이터는 초기화하지 않는다.

브라우저 테스트는 `frontend/tests/talk.browser.mjs`다. Chrome과 Playwright가 필요하며 `PLAYWRIGHT_MODULE`에 설치된 모듈 파일 URL, `TALK_QA_URL`에 개발 화면 주소를 지정한다. 최초 검증은 실제 환경 파일을 포함하지 않는 `.dev/talk-preview` 복사본의 3011 포트, 최신 main 반영 후 검증은 `.dev/talk-pr-project` 격리 프로덕션 빌드의 3012 포트에서 수행했다. 두 검증 모두 API를 전부 가로챘다. 테스트 화면 캡처는 Git-ignored `.dev/talk-qa/`에 저장한다. 별도 임시 도구 설치는 루트·frontend 의존성 파일을 변경하지 않았다.

## Jira 기록과 공유 설계

[GOMIN-69 구현 기록](https://younkim.atlassian.net/browse/GOMIN-69?focusedCommentId=10039)과 [GOMIN-70 QA 기록](https://younkim.atlassian.net/browse/GOMIN-70?focusedCommentId=10040)에 결과·한계·검수 22개·후속 계약을 기록했다. 명세 체크박스와 이슈 상태는 변경하지 않았다. [공유 설계](https://younkim.atlassian.net/wiki/spaces/GOMIN/pages/3670056)는 설계문서 DB 하위 게시·GOMIN-69 행 등록·본문과 부모/DB 행 재조회를 확인했다.

## 남은 통합 검증

실제 키를 사용하는 Codyssey 응답·요약 품질, Supabase Data API·세션 쿠키·실제 AI를 함께 사용하는 전체 흐름, 운영 DB 적용·배포, 실기기의 한국어 IME와 가상 키보드, 여러 DB 연결의 경합을 확인해야 한다. 김지민 담당의 이미지·완료·컬렉션 자체 동작은 이번 검증 범위에 포함하지 않으며 확정 요약 ID 전달과 기존 화면 진입까지 검증한다.

[구현·전달 계약](talk-mvp.md) · [문서 목록](../README.md)
