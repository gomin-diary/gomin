# 요약 기반 그림일기 MVP

저장된 요약 → 이미지 생성 → 컬렉션 저장 → 목록 조회 → 상세 조회를 구현한다.
요약 생성은 기존 대화 기능의 책임이며 브라우저가 임의의 요약 본문을 생성 API에 보내지 않는다.

## 이미지 생성

로그인 후 `/talk?summary=<저장된 요약 UUID>`에서 요약을 확인하고 그림을 생성한다.
대화 기능은 요약 저장 후 이 경로로 연결한다. summary 없이 접속하면 기존 준비 화면이다.

- `GET /api/v1/summaries/{summary_id}`: 세션 회원의 요약 조회
- `POST /api/v1/diary-images`, 본문 `{"summary_id":"UUID"}`: 요약 확인·제목/위로/프롬프트 구성·이미지 생성·파일과 결과 저장 후 201 반환
- `GET /api/v1/diary-results/{result_id}`: 본인의 생성 결과 재조회

이미지 생성은 HTTP 요청 안에서 직접 수행한다. 이미지 작업 큐·worker·lease·상태 폴링·자동 재시도는 없다.
생성 실패는 공통 오류 응답으로 반환하며 화면에서 다시 요청할 수 있다.

## 제공자와 설정

`backend/.env.example`의 서버 설정을 사용한다. 실제 키를 프론트나 Git에 저장하지 않는다.

| 설정 | 기본값/용도 |
| --- | --- |
| `AI_API_KEY` | 서버 환경변수의 가상 키, 기본 빈 값 |
| `AI_BASE_URL` | `https://copa.codyssey.kr` |
| `AI_TEXT_MODEL` | `gpt-5.4-mini` |
| `AI_IMAGE_MODEL` | `gpt-image-2` |
| `AI_IMAGE_SIZE` | `1024x1024` |
| `AI_TIMEOUT_SECONDS` | 개별 제공자 요청 120초 |
| `DIARY_IMAGE_BUCKET` | 비공개 `gomin-diary-images` |

텍스트는 `/v1/chat/completions`, 이미지는 `/api/v1/images`에 POST한다.
인증은 Bearer 가상 키, 본문은 JSON이다. 이미지 요청은 model/prompt/size와 `response_format=b64_json`을 사용한다.
첨부 예제의 `result.images[0].b64_json`을 디코딩해 실제 이미지 형식을 확인하고 Storage에 저장한다.
제공자의 웹 세션 전용 URL을 사용하지 않는다. DB에는 이미지 bucket/object key만 저장하고 조회 시 서명 URL을 발급한다.

## DB 변경

이미 적용·공유한 SQL 파일은 보존한다. 새 보정 마이그레이션에서 이미지 큐 함수를 제거하고
`diary_results.generation_job_id`를 nullable로 바꾼다. 새 이미지 결과는 job 없이 summary에 직접 연결한다.
기존 기록과 대화·요약 생성 관련 스키마는 보존한다. 소유권 검증과 기존 요약 확정 제약은 유지한다.

제공자 호출은 모의 응답으로 검증하며 실제 API 키를 사용한 생성 및 운영 DB 적용은 별도 확인이 필요하다.

[ERD](conversation-collection-erd.md) · [마이그레이션](database-migrations.md) · [문서 목록](../README.md)
