# 그림일기·컬렉션 API

서버는 자체 세션으로 회원을 확인한다. 클라이언트가 회원 ID나 요약 본문을 전달하지 않는다.
업무 데이터의 직접 접근 및 RPC 실행은 `service_role`에만 허용한다.

## 이미지 작업 접수

`POST /api/v1/conversations/{conversation_id}/image-jobs`에 `summary_id`와 UUID
`idempotency_key`를 보낸다. 성공 응답은 공통 규격의 202와 작업 ID·상태이며 실행 토큰은 노출하지 않는다.

새 `submit_diary_image` RPC는 회원과 대화·요약 소유권, 최신 요약 버전과 대화 범위를 검사한 뒤
최초 요약 확정·작업 INSERT·대화의 generating 전환을 함께 커밋한다.
동일 회원·요청 키는 기존 작업을 반환하고 다른 입력 fingerprint는 409다.
재전송은 이미 실패한 작업을 실행하지 않으며, 기존 작업 조회는 후속 대화 변경에도 유지된다.

서버가 요약 ID·모델·해상도·프롬프트 버전을 정규화해 fingerprint를 만든다.
`image_job_inputs`는 작업별 실제 모델과 옵션을 변경 없이 보관하여 서버 재시작 후에도 같은 입력을 사용한다.
`AI_IMAGE_SIZE` 기본값은 첨부 예제의 `1024x1024`이며 제공자 지원 규격으로 설정한다.
요약은 상위 대화 기능에서 생성해 둔 DB 행을 사용한다.

## 실행권과 재시작

작업은 DB의 queued 행으로 남는다. `claim_diary_image`는 `FOR UPDATE SKIP LOCKED`로
하나를 running으로 전환하고 실행별 토큰·시도 횟수·기본 600초 lease를 반환한다.
브라우저 응답의 성공과 생성 완료는 별개이며 워커는 DB 큐를 사용한다.
`expire_diary_image_leases`는 만료 작업을 LEASE_EXPIRED 실패로 전환한다.
제공자 처리 여부가 불확실하므로 만료 작업을 자동으로 다시 호출하지 않는다.
명시적으로 같은 작업을 재접수한 후 새 실행권을 받는 흐름에서 이전 토큰은 재사용할 수 없다.

## 결과 확정

`fail_diary_image`는 현재 토큰과 만료를 확인하고 허용한 오류 코드만 저장한다.
제공자 응답 본문·키·개인정보는 오류 열에 넣지 않는다. 늦은 실패는 현재 실행 상태를 덮어쓰지 않는다.
`retry_diary_image`는 서버에서 명시적으로 호출할 때만 같은 작업을 queued로 되돌린다.
입력·요청 키·작업 ID·기존 시도 횟수는 유지하며 다음 claim에서 새 토큰을 발급한다.
자동 재시도와 사용자용 재시도 버튼은 추가하지 않는다.

`finalize_diary_image`는 현재 실행 토큰과 만료 시각을 검사한 뒤 결과 INSERT와 작업 성공,
완료 시각 및 대화 ready 전환을 함께 커밋한다. 다른 활성 작업이 있으면 generating을 유지한다.
반복 완료는 최초 결과를 반환하며 제목·문구·경로·완료 시각을 변경하지 않는다.
한국 날짜는 DB의 completed_at 생성 컬럼으로 정한다. DB 커밋 실패를 생성 성공으로 반환하지 않는다.
Storage 업로드 이후 커밋이 실패하면 객체가 남을 수 있으며 자동 삭제하지 않는다.

## 컬렉션 저장

`POST /api/v1/diary-results/{result_id}/collection-entry`는 완료 결과 ID만 사용한다.
세션 회원이 소유한 결과를 `save_collection_result` RPC로 저장하고 항목 ID·결과 ID·최초 saved_at을 반환한다.
동일 결과는 기존 항목을 반환하여 재클릭·재전송·응답 유실 복구 때 저장 시각을 바꾸지 않는다.
없는 결과와 타인 결과는 모두 404다. 제목·날짜·이미지·요약은 원본 결과와 연결하며 요청 본문으로 덮어쓰지 않는다.

## 컬렉션 목록

`GET /api/v1/collection?limit=24&cursor=...&emotion=...`는 본인의 저장 항목만 반환한다.
`saved_at DESC, id DESC`로 정렬하고 두 값을 포함하는 불투명 next_cursor로 다음 페이지를 조회한다.
limit는 1~100이며 끝에서는 next_cursor가 null이다. 0건은 성공한 빈 items다.
항목 ID와 source_result_id, summary_id, conversation_id를 구분하고 일기 날짜는 diary_date다.
emotion은 원본 emotion_tags의 정확한 문자열 일치로 전체 DB 목록에 적용한다.
화면의 기쁨·슬픔·불안·관계·일상은 같은 이름의 태그에만 매핑하며 자동 분류를 추가하지 않는다.

`GET /api/v1/collection/{entry_id}`는 같은 회원의 항목→완료 결과→생성에 사용한 요약을 조인한다.
최신 요약으로 바꾸지 않으며 주요 고민·감정 태그 순서도 원본대로 반환한다. 타인과 없는 항목은 같은 404다.

[AI 설정](ai-client.md) · [대화·컬렉션 ERD](conversation-collection-erd.md) · [문서 목록](../README.md)
