# 털어놓기 MVP 구현과 후속 전달

기능 기준은 [GOMIN-71 최종 명세](https://younkim.atlassian.net/browse/GOMIN-71) 본문(2026-10-08 12:23:18 +09:00 수정)이다. 개발은 GOMIN-69, 검증은 GOMIN-70에 연결한다. 기획 작업의 상태를 구현 완료 근거로 사용하지 않는다.

## 구현 범위와 현재 실행 조건

HW 범위는 REST 대화 입력·저장·조회, 저장된 맥락의 AI 응답, 마무리·요약·확정·동일 대화 재개·재요약, 확정 요약 전달과 단계별 안내다. 확정 후 main의 기존 그림일기 화면으로 연결하며 김지민 담당의 이미지·완료·컬렉션 구현을 재사용한다.

대화·요약의 `CodysseyTalkProvider`는 main의 `CodysseyClient`를 기존 `get_ai_client` 의존성으로 주입받는다. 모델과 주소를 따로 하드코딩하지 않고 `backend/.env.example`의 `AI_BASE_URL`·`AI_TEXT_MODEL`·`AI_API_KEY` 설정을 재사용한다. 기본 텍스트 모델은 `gpt-5.4-mini`, 게이트웨이는 `https://copa.codyssey.kr/v1/chat/completions`다. 키가 없거나 잘못되면 `AI_NOT_CONFIGURED`로 실패하며 고정 문구로 대체하지 않는다. 실제 키를 사용한 AI 호출·품질 검증은 수행하지 않았다. 실제 비밀 키는 채팅·코드·문서에 넣지 않는다. 환경 안내는 frontend·backend의 `.env.example`만 기준으로 한다.

2026-10-09 로컬 Supabase에 대화 SQL과 main의 미적용 마이그레이션 12개를 적용했다. 적용 이력과 대화 RPC 7개 등록을 재조회하고 service_role의 저장·소유권·전송 제한·복원·재요약·확정·기존 그림일기 요약 참조를 실제 DB에서 검증했다. 검증용 회원·대화·결과는 트랜잭션에서 롤백했다. 최초 연결 거부 이후의 적용 성공이며, Supabase Data API·쿠키·실제 AI를 함께 사용하는 통합 검증과 운영 DB 적용은 남아 있다. [QA 기록](talk-mvp-qa.md)은 확인 범위를 구분한다.

## 화면과 입력

- `/talk`: 새 대화. 최초 전송 때 대화를 생성하고 서버가 사용자 메시지를 저장하면 `/talk/{conversation_id}`로 주소를 바꾼다.
- `/talk/{conversation_id}`: 서버에 저장된 원문·순서·시간, 진행 중인 작업과 요약을 조회한다.
- `/talk/{conversation_id}/handoff/{summary_id}`: 서버에서 확정 여부·소유권을 다시 확인하고 확정 요약을 표시한다.
- `/talk?summary={summary_id}`: main에 추가된 기존 그림일기 화면 경로를 보존한다. 대화 시작 화면은 summary 쿼리 없이 표시한다.
- 모든 경로는 기존 AuthGuard를 거친다. 로그인 복귀 경로는 허용된 UUID 대화·전달 주소만 추가했다.
- 기존 PageShell의 대화 배경·폰트·메뉴 숨김과 뒤로가기 자산을 재사용한다. Conversation, Wrap up, Summary의 PC·모바일 Figma 화면을 데스크톱 앱에서 직접 확인했다.
- 입력 길이는 Unicode 코드 포인트로 계산한다. 공백·줄바꿈을 포함해 최대 100자이고 빈 입력·공백만 있는 입력·101자 이상은 전송하지 않는다. 서버와 SQL에서도 검사한다.
- PC Enter는 전송, Shift+Enter는 줄바꿈이다. 모바일 화면 또는 터치 입력 기기는 Enter로 줄바꿈한다. composition 상태·native isComposing·keyCode 229를 검사한다.
- 응답 대기 중에도 작성·수정할 수 있지만 추가 전송은 막는다. 정상 대기 중 새로 작성한 입력은 응답 완료 후 유지하고 자동 전송하지 않는다.
- 초안은 메모리에만 둔다. 재접속·새로고침·계정 변경 후 복원하지 않는다. 실패한 전송의 초안을 별도로 저장하거나 복구하지 않는다.
- 요약은 문장·목록·태그로 표시하고 버전·반영한 마지막 순번을 함께 보여 준다. 요약 직접 편집은 제공하지 않는다.

## 응답 대기 중 마무리와 원문 범위

첫 사용자 메시지가 서버에 저장됐다는 응답을 받는 순간부터 마무리를 활성화한다. AI 완료·AI 판단·대화 횟수를 조건으로 추가하지 않는다. 이미 저장된 대화에서는 다음 메시지의 저장 응답을 기다리는 동안에도 마무리를 선택할 수 있다.

1. 마무리를 선택하면 즉시 Wrap up으로 이동한다. 입력창은 계속 제공하며 초안이 요약에 포함되지 않는다고 안내한다.
2. 접수 중인 전송이 있다면 저장 결과를 기다린다. 저장 여부를 확인하지 못하면 요약을 시작하지 않고 보류를 표시한다.
3. 진행 중인 모리 응답 한 건의 성공·실패를 기다린다. 상태 조회가 실패하면 요약을 시작하지 않는다. 실패 또는 시간 초과로 종료된 응답은 정상 원문으로 만들지 않는다.
4. 요약 접수 RPC가 대화를 잠그고 저장된 최대 순번을 `source_until_seq_no`에 고정한다. 진행 중인 응답·요약이 있으면 접수를 거절한다.
5. 해당 대화에서 이 순번 이하의 저장된 사용자·모리 원문만 순서대로 제공자에 전달한다. 다른 대화나 전송 전 초안은 전달하지 않는다.
6. 성공한 요약은 같은 잠금 안에서 새 버전으로 저장한다. 실패한 요약은 완성 결과로 표시하지 않는다.
7. 같은 대화 재개는 phase만 chatting으로 전환한다. 원문·시각·이전 요약은 보존한다. 추가 대화 후 다시 마무리하면 새 버전과 새 반영 범위를 만든다.
8. 확정은 현재 표시한 요약 ID를 사용한다. 서버는 소유권·최신 버전·현재 저장 순번과의 일치·진행 작업 여부를 검사한다. 오래된 요약 확정은 409로 거절한다.

원문 삭제나 영구 종료는 하지 않는다. 기존 SQL의 최신 요약 확정 제약과 일치하도록, 늦은 응답이 성공한 후에는 그 응답까지 저장된 범위에 포함한다.

## 인증·API 계약

호출은 `apiFetch`와 세션 쿠키를 사용한다. 서버는 모든 경로에서 `require_member`로 확인한 회원 ID를 DB에 전달한다. 요청 본문의 회원 ID는 받지 않는다. 비소유 대화·요약은 404로 응답하고 내부 DB 오류는 비밀정보 없는 공통 오류로 변환한다.

채팅은 HTTP REST API를 사용한다. 메시지 POST는 사용자 원문 저장과 응답 작업 접수 후 즉시 202를 반환한다. 브라우저는 같은 대화 GET을 800ms 간격으로 조회해 저장된 모리 응답·작업 실패를 확인한다. 202는 AI 완료가 아니다. 응답·요약 생성은 한 번만 실행하며 조회 실패 시 관찰을 중단한다. WebSocket·SSE·토큰 스트리밍은 사용하지 않는다.

아래는 공통 성공 응답의 `data`다. 경로 접두사는 `/api/v1/conversations`다.

| 메서드·경로 | 입력 | 성공 결과 |
| --- | --- | --- |
| POST / | 없음 | 201: 대화 ID·phase·messages·summaries·jobs |
| GET /{conversation_id} | 없음 | 200: 원문·요약·응답/요약 작업 스냅샷 |
| POST /{conversation_id}/messages | content, client_message_id(UUID) | 202: 저장된 message, job |
| POST /{conversation_id}/summaries | request_id(UUID) | 202: 요약 job |
| POST /{conversation_id}/resume | 없음 | 200: 같은 대화 스냅샷 |
| POST /{conversation_id}/summaries/{summary_id}/confirm | 없음 | 200: ConfirmedSummaryHandoff |
| GET /{conversation_id}/summaries/{summary_id}/handoff | 없음 | 200: 서버에서 다시 조회한 ConfirmedSummaryHandoff |

message에는 ID·conversation_id·seq_no·role·content·created_at이 있다. 시간은 서버 저장 시각을 그대로 전달하고 화면에서 현지 날짜·시간으로 표시한다. summary에는 ID·conversation_id·version·source_until_seq_no·세 영역·confirmed_at·created_at이 있다. job에는 ID·kind·status·source_until_seq_no·error_code만 공개하며 lease·내부 요청 지문은 공개하지 않는다.

주요 오류는 401 UNAUTHORIZED, 404 NOT_FOUND, 409 TALK_BUSY/TALK_EMPTY/STALE_SUMMARY/CONFLICT/SUMMARY_NOT_CONFIRMED, 422 VALIDATION_ERROR, 503 SERVICE_UNAVAILABLE이다. AI 작업 실패는 job의 AI_NOT_CONFIGURED/AI_FAILED/AI_TIMEOUT으로 구분한다. 응답·요약 로딩과 실패·확정 실패를 별도로 표시한다.

## 김지민 담당 연결 지점

`frontend/src/lib/talk.ts`의 `SummaryHandoff`와 `backend/app/schemas/talk.py`의 `ConfirmedSummaryHandoff`가 전달 계약이다.

```json
{
  "conversation_id": "<대화 UUID>",
  "summary_id": "<서버 요약 UUID>",
  "version": 2,
  "confirmed": true,
  "summary": {
    "id": "<동일 요약 UUID>",
    "conversation_id": "<동일 대화 UUID>",
    "version": 2,
    "source_until_seq_no": 4,
    "current_feeling": "<서버 저장 문장>",
    "main_concerns": ["<서버 저장 고민>"],
    "emotion_tags": ["<서버 저장 감정>"],
    "confirmed_at": "<서버 확정 시각>",
    "created_at": "<서버 생성 시각>"
  },
  "next_stage": "image_generation",
  "next_stage_status": "not_started"
}
```

- `TalkSession`의 `onConfirmed(handoff)`는 서버 확정 응답 또는 확정 요약 조회 후 전달한다. `ConfirmedSummaryBoundary`의 그림일기 이동 링크는 확정된 `summary_id`로 main의 `/talk?summary={summary_id}`를 연다. 로그인 복귀도 이 UUID 쿼리 경로만 허용한다.
- 독립적인 후속 화면은 handoff GET 경로로 동일 서버 데이터를 다시 읽는다. 서버의 `TalkRepository.confirmed_summary(member_id, conversation_id, summary_id)`도 사용할 수 있다.
- 후속 API는 브라우저가 보낸 summary 본문이나 confirmed=true를 신뢰하지 말고 세션 회원과 위 식별자로 서버 저장·소유권·확정을 검증한다.
- main의 후속 이미지 구현은 `/talk?summary={summary_id}`와 `POST /api/v1/diary-images`의 `summary_id`로 저장 요약을 참조한다. 이미지 결과는 작업 큐 없이 `diary_results.summary_id`에 직접 연결한다. 기존 [그림일기 MVP](diary-mvp.md)와 [공통 ERD](conversation-collection-erd.md)를 따른다.
- HW 확정 API와 화면 이동은 이미지 job·diary_results·collection_entries를 만들지 않는다. 전달 화면은 요약 확정과 이미지·저장 미시작을 구분한다. 이미지 생성은 기존 후속 화면의 별도 버튼에서 시작한다.

## 저장과 실행 방식

[새 마이그레이션](../../supabase/migrations/20261008044707_talk_mvp_commands.sql)은 기존 conversations·conversation_messages·conversation_summaries·generation_jobs를 재사용한다. 기존 공유 SQL과 제약조건은 보존했다. seed·이미지·컬렉션 변경은 없다.

`gomin_talk_send/start_summary/complete/resume/confirm`은 대화 행 잠금으로 순번·버전·완료·확정을 원자적으로 처리한다. `gomin_talk_snapshot`은 전체 원문을 순서대로 집계해 Data API 행 수 상한으로 원문이 잘리는 것을 피한다. 모든 RPC는 security invoker, 빈 search_path, service_role 전용 실행 권한을 사용한다.

프론트는 새 전송·요약에 UUID를 한 번 발급한다. 기존 식별자·UNIQUE와 동일 요청 키 반환은 유지하지만, UI의 재전송·독립적인 중복 실행 방지·실패 재시도는 추가하지 않았다. 같은 키로 실패 작업을 조회해도 재실행하지 않는다.

AI 실행은 FastAPI BackgroundTasks에서 한 번 수행하고 60초로 제한한다. DB 실행 lease는 90초이며 늦은 완료는 저장하지 않는다. 서버 종료나 DB 장애로 완료 상태를 기록하지 못하면 만료된 작업을 조회 시 실패로 표시한다. 자동 재실행·재시도 worker·복구 화면은 없다. 진행 상태의 GET 조회만 800ms 간격으로 수행하며 네트워크 실패 시 중단한다.

응답 프롬프트는 해당 원문 범위의 사용자·모리 역할과 내용을 순서대로 전달한다. 요약은 같은 원문을 JSON 자료로 전달하고 세 영역의 JSON 출력·빈 값·길이·추가 필드를 검증한다. 회원 ID·대화 ID·시각·초안은 제공자에 전달하지 않는다. 미설정은 AI_NOT_CONFIGURED, 제공자/전체 실행 시간 초과는 AI_TIMEOUT, 통신·잘못된 출력은 AI_FAILED로 기록한다. 제공자의 원문 오류는 화면·로그·DB에 그대로 노출하지 않는다.

## 적용과 검증

DB 적용은 [마이그레이션 관리](database-migrations.md)의 `npm run db:migrate`와 운영 절차를 따른다. 기존 DB를 검증 목적으로 reset하지 않는다. 제공자 어댑터와 로컬 SQL 적용은 확인했으며, 쿠키 인증부터 실제 AI 응답·요약·확정까지의 통합 검증과 운영 적용은 남아 있다.

[공유 설계 검토안](https://younkim.atlassian.net/wiki/spaces/GOMIN/pages/3670056) · [검수 22개와 실행 결과](talk-mvp-qa.md) · [문서 목록](../README.md)
