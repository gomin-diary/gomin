# 털어놓기 MVP 구현과 후속 전달

기능 기준은 [GOMIN-71 최종 명세](https://younkim.atlassian.net/browse/GOMIN-71) 본문(2026-10-08 12:23:18 +09:00 수정)이다. 개발은 GOMIN-69, 검증은 GOMIN-70에 연결한다. 기획 작업의 상태를 구현 완료 근거로 사용하지 않는다.

## 구현 범위와 현재 실행 조건

HW 범위는 대화 입력·저장·조회, 저장된 맥락의 AI 호출 경계, 마무리·요약·확정·동일 대화 재개·재요약, 확정 요약 전달과 단계별 안내다. 김지민 담당의 이미지 생성·재생성·완료 화면·컬렉션 저장은 연결 지점 이후 별도 구현이다.

이 PR의 대화·요약은 `TalkProvider` 인터페이스까지 구현했으며 기본 구현은 `AI_NOT_CONFIGURED` 실패를 기록한다. 실제 AI 대신 고정 문구를 반환하지 않는다. 최초 구현 당시 제공자 합의는 확인되지 않았으나, PR 생성 중 main에 `CodysseyClient`와 텍스트 모델 `gpt-5.4-mini` 설정이 추가됐다. 해당 클라이언트를 사용하는 대화·요약 어댑터 등록과 실제 호출은 이 PR에서 확인하지 않았다. 실제 비밀 키는 채팅·코드·문서에 넣지 않는다. 환경 안내는 `backend/.env.example`, `frontend/.env.example`만 기준으로 한다.

새 SQL 파일은 작성했으나 실제 Supabase 적용은 아직 확인하지 않았다. 최초 적용 시도는 로컬 DB 연결(127.0.0.1:54322) 거부로 실패했다. 이후 Docker의 supabase_db_gomin 컨테이너가 healthy 상태이고 같은 포트에 연결되는 것을 확인했다. SQL 적용 재실행은 하지 않았다. [QA 기록](talk-mvp-qa.md)은 격리된 검증과 실제 연동·배포 여부를 구분한다.

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

- `TalkSession`의 `onConfirmed(handoff)`는 서버 확정 응답 또는 확정 요약 조회 후 전달한다. `ConfirmedSummaryBoundary`를 후속 화면으로 교체할 수도 있다.
- 독립적인 후속 화면은 handoff GET 경로로 동일 서버 데이터를 다시 읽는다. 서버의 `TalkRepository.confirmed_summary(member_id, conversation_id, summary_id)`도 사용할 수 있다.
- 후속 API는 브라우저가 보낸 summary 본문이나 confirmed=true를 신뢰하지 말고 세션 회원과 위 식별자로 서버 저장·소유권·확정을 검증한다.
- main의 후속 이미지 구현은 `/talk?summary={summary_id}`와 `POST /api/v1/diary-images`의 `summary_id`로 저장 요약을 참조한다. 이미지 결과는 작업 큐 없이 `diary_results.summary_id`에 직접 연결한다. 기존 [그림일기 MVP](diary-mvp.md)와 [공통 ERD](conversation-collection-erd.md)를 따른다.
- HW 확정 API는 이미지 job·diary_results·collection_entries를 만들지 않는다. 전달 화면은 다음 단계 보류를 표시한다. 실제 이미지 작업을 시작한 뒤에는 후속 담당이 자체 상태를 조회·표시해야 한다.

## 저장과 실행 방식

[새 마이그레이션](../../supabase/migrations/20261008044707_talk_mvp_commands.sql)은 기존 conversations·conversation_messages·conversation_summaries·generation_jobs를 재사용한다. 기존 공유 SQL과 제약조건은 보존했다. seed·이미지·컬렉션 변경은 없다.

`gomin_talk_send/start_summary/complete/resume/confirm`은 대화 행 잠금으로 순번·버전·완료·확정을 원자적으로 처리한다. `gomin_talk_snapshot`은 전체 원문을 순서대로 집계해 Data API 행 수 상한으로 원문이 잘리는 것을 피한다. 모든 RPC는 security invoker, 빈 search_path, service_role 전용 실행 권한을 사용한다.

프론트는 새 전송·요약에 UUID를 한 번 발급한다. 기존 식별자·UNIQUE와 동일 요청 키 반환은 유지하지만, UI의 재전송·독립적인 중복 실행 방지·실패 재시도는 추가하지 않았다. 같은 키로 실패 작업을 조회해도 재실행하지 않는다.

AI 실행은 FastAPI BackgroundTasks에서 한 번 수행하고 60초로 제한한다. DB 실행 lease는 90초이며 늦은 완료는 저장하지 않는다. 서버 종료나 DB 장애로 완료 상태를 기록하지 못하면 만료된 작업을 조회 시 실패로 표시한다. 자동 재실행·재시도 worker·복구 화면은 없다. 진행 상태의 GET 조회만 800ms 간격으로 수행하며 네트워크 실패 시 중단한다.

## 적용과 검증

DB 적용은 [마이그레이션 관리](database-migrations.md)의 `npm run db:migrate`와 운영 절차를 따른다. 기존 DB를 검증 목적으로 reset하지 않는다. 제공자 등록·실제 DB 적용 후 쿠키 인증부터 응답·요약·확정까지 실제 통합 검증이 남아 있다.

[공유 설계 검토안](https://younkim.atlassian.net/wiki/spaces/GOMIN/pages/3670056) · [검수 22개와 실행 결과](talk-mvp-qa.md) · [문서 목록](../README.md)
