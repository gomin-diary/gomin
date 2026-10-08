# Codyssey AI 요청 설정

백엔드는 Codyssey 제공자의 텍스트·이미지 요청을 별도 경로와 모델로 구성한다. 설정은
[backend/.env.example](../../backend/.env.example)을 기준으로 운영 환경변수 또는 백엔드 환경파일에 입력한다.
실제 키는 소스·Jira·프론트엔드·로그에 기록하지 않는다.

## 환경변수

| 설정 | 기본값 | 의미 |
| --- | --- | --- |
| `AI_BASE_URL` | `https://copa.codyssey.kr` | 경로·쿼리·인증정보 없는 HTTPS origin |
| `AI_API_KEY` | 빈 값 | 백엔드 전용 가상 키, 요청 구성 시 필수 |
| `AI_TEXT_MODEL` | `gpt-5.4-mini` | 텍스트/프롬프트 요청 모델 |
| `AI_IMAGE_MODEL` | `gpt-image-2` | 이미지 요청 모델, 환경변수로 재정의 가능 |
| `AI_IMAGE_SIZE` | `1024x1024` | 이미지 접수 시 보관하는 제공자 해상도 옵션 |
| `AI_IMAGE_RESPONSE_FORMAT` | `b64_json` | 허용하는 이미지 응답 형식 |
| `AI_TIMEOUT_SECONDS` | `120` | 요청별 제한 시간, 0 초과 600 이하의 유한한 값 |

`AI_API_KEY`는 `SecretStr`로 관리하며 설정 객체의 문자열·JSON 표현에서 마스킹된다.
인증 헤더를 만들 때만 실제 값을 사용한다. 키가 없거나 공백·제어문자·비 ASCII 문자를 포함하면
`AIConfigurationError`로 거절하며 오류에는 키 값을 넣지 않는다.
AI 설정은 앱 시작에 필수가 아니며 요청을 구성할 때 검사하므로 다른 API는 키 없이 시작할 수 있다.

## 요청 경로와 모델

Public origin으로부터 두 경로를 구성한다. `AI_BASE_URL`에 `/v1`을 포함하면 설정 오류다.

| 요청 | 기본 URL | 본문 |
| --- | --- | --- |
| 텍스트 | `POST https://copa.codyssey.kr/v1/chat/completions` | `model`, `messages` |
| 이미지 | `POST https://copa.codyssey.kr/api/v1/images` | `model`, `prompt`, `size`, `response_format` |

OpenAI 호환 base는 `Settings.ai_openai_base_url`의 `https://copa.codyssey.kr/v1`이다.
이미지 경로는 호환 base에 붙이지 않는다. 두 요청 모두 서버의 가상 키로
`Authorization: Bearer <virtual-key>`와 `Content-Type: application/json`을 구성한다.

사용자 지정 기본 모델은 텍스트 `gpt-5.4-mini`, 이미지 `gpt-image-2`다.
`AI_IMAGE_MODEL` 환경변수가 없으면 이미지 기본값을 사용하고, 설정한 값이 있으면 그 값을 사용한다.
명시적으로 빈 문자열을 설정하면 이미지 요청 구성 시 오류로 거절한다.
제공자 사진의 `gpt-image-1-mini`는 참고 예제이며 프로젝트 이미지 기본값으로 사용하지 않는다.
이미 접수한 작업은 DB에 기록한 모델을 유지한다. 모델의 실제 사용 가능 여부는 제공자에서 확인한다.

제공자 사진에 따르면 이미지 응답 `url`은 웹 로그인 세션 전용이므로 `b64_json`을 요청한다.
참고 응답 경로는 `result.images[0].b64_json`이다. 이후 이미지 어댑터에서 디코딩·형식·크기를 검증하고
비공개 Storage에 업로드한다. DB에는 버킷·객체 경로만 저장하고, 브라우저에는 우리 Storage의 서명 URL을 제공한다.

## 모듈과 호출

- [client.py](../../backend/app/ai/client.py)의 `CodysseyClient`는 텍스트·이미지 HTTP 요청을 구성한다.
- [dependencies.py](../../backend/app/ai/dependencies.py)의 `get_ai_client`를 FastAPI `Depends`로 주입한다.
- [main.py](../../backend/app/main.py)의 앱 수명 주기가 기존 비동기 HTTP 클라이언트를 주입·종료한다.

```python
from app.ai.client import CodysseyClient

client = CodysseyClient(http_client, settings)
text_request = client.build_text_request([
    {"role": "user", "content": "오늘의 고민을 정리해 주세요."},
])
image_request = client.build_image_request(prompt, size="1024x1024")
```

두 메서드는 `httpx.Request`를 반환하며 네트워크 전송은 하지 않는다. 요청에는 인증 헤더가 있으므로
요청 객체·헤더 전체를 로그나 응답에 출력하지 않는다. 모델 응답 처리·생성 작업·DB 저장은 별도 호출 기능에서 구현한다.
해상도는 호출자가 제공하며 사진 예시의 `1024x1024`를 서비스 정책으로 고정하지 않는다.

`await client.generate_image(prompt, size=...)`는 이미지 요청을 한 번 전송하고
`result.images[0].b64_json`을 엄격히 디코딩해 `bytes`로 반환한다. 응답의 세션 전용 URL은 사용하지 않는다.
응답 본문과 디코딩 바이트 크기를 제한하며, 실제 이미지 형식은 업로드 호출부에서 검증한다.
리다이렉트·자동 재시도는 하지 않는다. 요청 전체 제한 시간과 HTTP I/O 제한 시간을 적용한다.

`AIRequestError`는 안전한 오류 코드와 요청 결과가 불확실한지를 나타내는 `uncertain`을 제공한다.
연결 실패는 `CONNECTION_FAILED`, 시간 초과는 `TIMEOUT`, 429는 `RATE_LIMITED`, 그 외 비정상 상태는
`PROVIDER_ERROR`, 잘못된 응답은 `INVALID_RESPONSE`, 응답 크기 초과는 `RESPONSE_TOO_LARGE`다.
타임아웃·서버 오류·잘못된 성공 응답 후에는 제공자가 이미 처리했을 수 있으므로 자동으로 다시 생성하지 않는다.
제공자 오류 본문·인증 헤더·Base64를 오류 메시지에 포함하지 않는다.

## 생성 이미지 저장

`get_diary_image_storage`로 주입한 저장 모듈은 PNG·JPEG·WebP의 실제 파일 형식을 확인하고
전체 픽셀을 디코딩한 뒤 기존 `SupabaseFileStorage`로 업로드한다. 빈 파일·손상 파일·애니메이션·
10 MiB 초과 파일·`DIARY_IMAGE_MAX_PIXELS` 초과 이미지는 업로드 전에 거절한다.
기본 픽셀 상한은 16,777,216이며 환경변수로 더 낮출 수 있다.

새 마이그레이션은 `gomin-diary-images` 비공개 버킷을 만들고 크기·MIME 제한을 적용한다.
`DIARY_IMAGE_BUCKET`을 변경하면 동일 제한의 비공개 버킷을 별도로 준비해야 한다.
일반 회원의 직접 Storage 접근 정책은 추가하지 않는다. 반환값은 버킷과 임의 UUID 객체 경로이며,
제공자 URL·Base64·이미지 바이너리·서명 URL을 업무 테이블에 저장하지 않는다.
업로드 실패는 결과 경로를 반환하지 않는다. 업로드와 DB 커밋은 별도이므로 호출부에서 실패를 처리해야 한다.

## 검증

설정과 모의 HTTP 전송으로 기본·사용자 지정 origin의 최종 경로, Bearer/JSON 헤더, 모델 분리,
`b64_json` 요청, 제한 시간, 미설정·잘못된 키 거절과 마스킹을 확인한다.
실제 환경파일·가상 키·제공자 API를 사용하지 않는다.

```sh
PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests
```

[환경변수 안내](../local-development/environment.md) · [문서 목록](../README.md)
