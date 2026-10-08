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

[AI 설정](ai-client.md) · [대화·컬렉션 ERD](conversation-collection-erd.md) · [문서 목록](../README.md)
