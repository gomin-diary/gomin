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

## 컬렉션 저장

완성 카드의 저장 버튼은 `POST /api/v1/diary-results/{result_id}/collection-entry`를 호출한다.
서버는 세션 회원의 결과만 저장하며 같은 결과를 다시 저장하면 기존 컬렉션 항목을 반환한다.
화면은 저장 성공을 표시하고 `/collection#entry=<항목 UUID>` 링크를 제공한다.
저장에 실패하면 생성된 결과를 유지한 채 저장을 다시 요청할 수 있다.

## 컬렉션 목록

`GET /api/v1/collection`은 세션 회원이 저장한 항목만 최신 저장 순서로 반환한다.
목록은 항목 ID·제목·그림일기 날짜·감정 태그·서명 이미지 URL을 포함한다. 0건은 성공 빈 배열이다.
서버 커서 페이지네이션은 사용하지 않고 기존 화면의 6개 단위 이동과 감정 태그 필터를 유지한다.
서명 URL은 조회 시 발급하며 만료 후 화면을 새로 조회하면 갱신된다.

## 컬렉션 상세

`GET /api/v1/collection/{entry_id}`는 본인의 저장 항목 → 생성 결과 → 원본 요약을 조회한다.
제목·위로·날짜·이미지와 지금의 마음·주요 고민·감정 태그를 반환한다.
이후 새 요약이 생겨도 저장한 결과의 원본 요약은 바뀌지 않는다. 타인·미존재 항목은 같은 404로 처리한다.
기존 PC 팝업과 모바일 상세 화면에 연결하며 해시의 항목 ID로 직접 상세를 열 수 있다.

## 제공자와 설정

`backend/.env.example`의 서버 설정을 사용한다. 실제 키를 프론트나 Git에 저장하지 않는다.

| 설정 | 기본값/용도 |
| --- | --- |
| `AI_API_KEY` | Copa 텍스트 구성용 서버 전용 가상 키, 기본 빈 값 |
| `AI_BASE_URL` | `https://copa.codyssey.kr` |
| `AI_TEXT_MODEL` | `gpt-5.4-mini` |
| `AI_TIMEOUT_SECONDS` | Copa 요청 120초 |
| `GEMINI_API_KEY` | Google AI Studio에서 발급한 서버 전용 API 키, 기본 빈 값 |
| `GEMINI_BASE_URL` | `https://generativelanguage.googleapis.com` |
| `GEMINI_IMAGE_MODEL` | `gemini-2.5-flash-image` |
| `GEMINI_IMAGE_ASPECT_RATIO` | `1:1`, 기본 모델의 정사각형 출력은 1024×1024 |
| `GEMINI_TIMEOUT_SECONDS` | 개별 제공자 요청 120초 |
| `DIARY_IMAGE_BUCKET` | 비공개 `gomin-diary-images` |

제목·위로·이미지 프롬프트 구성은 기존 Copa의 `/v1/chat/completions`에 POST한다.
`AI_API_KEY`를 Bearer 인증으로 전달하고 `AI_TEXT_MODEL`과 system/user 메시지를 사용한다.
요약의 지금의 마음·주요 고민·감정 태그만 텍스트 구성 요청에 포함한다.
이미지 생성만 Gemini API의 `/v1beta/models/{모델 ID}:generateContent`에 POST한다.
`GEMINI_API_KEY`를 `x-goog-api-key` 헤더로 전달하며 Copa에서 만든 이미지 프롬프트와 모리 참조 이미지를 보낸다.
모리는 [원본 mori.png](../../frontend/public/images/character/mori.png)의 캐릭터로,
백엔드 단독 배포에도 포함되도록 [동일한 PNG](../../backend/app/assets/mori.png)를 서버 자산으로 보관한다.
이미지를 교체할 때는 두 파일을 함께 갱신하며 테스트에서 동일 바이트와 PNG 형식을 확인한다.
참조 파일은 실행 디렉터리와 무관한 모듈 기준 경로로 읽고, 서버 클라이언트가 Base64를 한 번 읽어 재사용한다.
Gemini 요청의 `contents.parts`에는 모리 외형·그림체 유지 지시, `inlineData`의 PNG 바이트,
요약 기반 장면 프롬프트를 함께 넣는다. 새싹·긴 귀·털색·표정 특징·초록 배낭을 유지하고 장면·자세·감정을 바꾼다.
이미지 요청은 `contents`와 `generationConfig.responseModalities=["TEXT","IMAGE"]`,
`generationConfig.imageConfig.aspectRatio`를 사용한다. 픽셀 크기를 직접 지정하지 않는다.
응답의 첫 후보가 `finishReason=STOP`인 경우만 사용하며 안전 차단·중단·이미지 없는 응답은 실패 처리한다.
`content.parts`에서 thought가 아닌 `inlineData.data`의 Base64를 디코딩해 실제 이미지 형식과 용량을 확인하고 Storage에 저장한다.
DB에는 이미지 bucket/object key만 저장하고 조회 시 서명 URL을 발급한다.

기존 Copa용 `AI_API_KEY`, `AI_BASE_URL`, `AI_TEXT_MODEL`, `AI_TIMEOUT_SECONDS`는 유지한다.
이미지용 `GEMINI_*` 설정을 추가한 뒤 백엔드를 재시작한다.
기존 `AI_IMAGE_MODEL`, `AI_IMAGE_SIZE`, `AI_IMAGE_RESPONSE_FORMAT`은 사용하지 않는다.
Gemini 키·이미지 모델이나 모리 참조 파일이 누락되면 유료 Copa 요청 전에 설정 오류를 반환한다.
키는 [Google AI Studio](https://aistudio.google.com/apikey)에서 발급하며,
요청·응답 규격은 [Gemini 이미지 생성 공식 문서](https://ai.google.dev/gemini-api/docs/generate-content/image-generation)를 따른다.

## DB 변경

이미 적용·공유한 SQL 파일은 보존한다. 새 보정 마이그레이션에서 이미지 큐 함수를 제거하고
`diary_results.generation_job_id`를 nullable로 바꾼다. 새 이미지 결과는 job 없이 summary에 직접 연결한다.
기존 기록과 대화·요약 생성 관련 스키마는 보존한다. 소유권 검증과 기존 요약 확정 제약은 유지한다.

제공자 호출은 모의 응답으로 검증하며 실제 API 키를 사용한 생성 및 운영 DB 적용은 별도 확인이 필요하다.

[ERD](conversation-collection-erd.md) · [마이그레이션](database-migrations.md) · [문서 목록](../README.md)
