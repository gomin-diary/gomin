# 공통 API 응답 모델

프론트엔드와 백엔드는 JSON API에서 같은 `success`, `data`, `error` 계약을 사용한다. Python과 TypeScript는 각 언어의 모델을 유지하며 공통 구조와 오류 코드를 일치시킨다. 이 문서는 현재 구현 규격과 새 API에 적용하는 방법을 설명한다.

## 성공과 실패

성공 응답 예시 — `GET /api/v1/health/db`, HTTP 200:

```json
{
  "success": true,
  "data": { "status": "ok", "database": "connected" },
  "error": null
}
```

실패 응답 예시 — HTTP 422:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해 주세요.",
    "details": [
      {
        "path": ["body", "count"],
        "code": "INVALID_FORMAT",
        "message": "입력 형식이 올바르지 않습니다."
      }
    ]
  }
}
```

| 필드 | 규칙 |
| --- | --- |
| `success` | 성공은 `true`, 실패는 `false` |
| `data` | 성공 시 API별 데이터, 실패 시 `null` |
| `error` | 성공 시 `null`, 실패 시 `code`, `message`, `details` 객체 |
| `error.code` | 화면 분기와 처리를 위한 고정 문자열 |
| `error.message` | 사용자에게 안내할 수 있는 문구. 프로그램 분기는 문구에 의존하지 않는다. |
| `error.details` | 필드별 오류 배열. 없으면 `[]` |
| `details[].path` | 선언된 입력 필드명·배열 인덱스의 문자열·정수 배열. 예: `["body", "items", 0, "name"]`. 동적 딕셔너리 키와 확인할 수 없는 경로는 `[redacted]`로 가린다. |

HTTP 2xx 응답은 성공 모델을 사용하고, HTTP 4xx·5xx 응답은 실패 모델을 사용한다. 실패를 HTTP 200으로 반환하지 않는다. JSON API는 데이터가 없더라도 HTTP 200과 `data: null`을 사용할 수 있다. HTTP 204, 파일 다운로드, 스트리밍은 별도 응답 방식을 사용하며 `apiFetch`로 호출하지 않는다. OpenAPI 및 Swagger 문서는 공통 JSON 래퍼로 감싸지 않는다.

## HTTP 상태와 오류 코드

| HTTP 상태 | 기본 코드 | 의미 |
| --- | --- | --- |
| 400 | `BAD_REQUEST` | 잘못된 요청 |
| 401 | `UNAUTHORIZED` | 인증 필요 |
| 403 | `FORBIDDEN` | 권한 부족 |
| 404 | `NOT_FOUND` | 대상 없음 |
| 405 | `METHOD_NOT_ALLOWED` | 허용되지 않은 요청 방식 |
| 409 | `CONFLICT` | 중복·상태 충돌 |
| 422 | `VALIDATION_ERROR` | 입력 검증 실패 |
| 429 | `RATE_LIMITED` | 요청 제한 |
| 500 | `INTERNAL_ERROR` | 예상하지 못한 서버 오류 |
| 503 | `SERVICE_UNAVAILABLE` | DB 등 의존 서비스 이용 불가 |

표에 없는 HTTP 예외는 원래 상태 코드를 유지하며, 4xx는 `HTTP_ERROR`, 5xx는 `INTERNAL_ERROR`로 표현한다. 업무별 오류는 `AppError`로 명시적인 코드를 정의한다. 공통 세션 API의 쿠키·업무 오류는 [공통 인증·DB 기반](auth-foundation.md)을 따른다.

입력 검증의 상세 코드는 필수 값 누락에 `REQUIRED`, 파싱·타입 오류와 잘못된 JSON에 `INVALID_FORMAT`, 그 외 검증 실패에 `INVALID_VALUE`를 사용한다. 검증기의 원본 `input`, `ctx`, `msg`를 응답으로 전달하지 않는다. 중첩 `Depends`에 선언한 query·path·header·cookie 필드도 오류 경로에 유지한다. 본문 필드의 `AliasChoices`·`AliasPath`는 검증 오류가 가리키는 선언된 별칭 경로를 유지하며, 그 아래의 동적 딕셔너리 키는 계속 가린다. 원래 필드명을 허용하는 `validate_by_name` 설정과 별칭 대신 필드명을 보고하는 `loc_by_alias=False` 설정도 반영한다. 쿼리 모델 내부의 선언된 필드명을 유지하며, 일반 모델 유니온(`A | B`)의 오류 경로에서는 Pydantic이 추가한 모델명 구분 표시를 제거한다. 배열 인덱스는 유지하고 동적 키와 알 수 없는 경로는 가린다.

## 백엔드 적용

| 파일 | 역할 |
| --- | --- |
| [response.py](../../backend/app/schemas/response.py) | `ApiSuccess[T]`, `ApiFailure`, 오류 및 health 데이터 모델 |
| [errors.py](../../backend/app/core/errors.py) | `AppError`와 HTTP 오류 코드·기본 문구 |
| [exception_handlers.py](../../backend/app/core/exception_handlers.py) | 공통 오류 변환, CORS 내부 오류 경계, OpenAPI 오류 모델 |
| [validation_error_paths.py](../../backend/app/core/validation_error_paths.py) | 선언된 필드·인덱스를 유지하고 동적 키를 가리는 검증 오류 경로 처리 |
| [main.py](../../backend/app/main.py) | 앱 구성과 예외 핸들러·라우터 등록 |
| [health.py](../../backend/app/api/routes/health.py) | health API와 DB 상태 확인 |

성공 모델은 엔드포인트에서 명시적으로 반환한다. 응답 전체를 자동으로 포장하는 미들웨어는 사용하지 않는다.

```python
@app.get("/api/v1/health", response_model=ApiSuccess[HealthData])
async def health() -> ApiSuccess[HealthData]:
    return ApiSuccess(data=HealthData())
```

예상 가능한 업무 실패는 `AppError(status_code, code, message, details=..., headers=...)`로 표현한다. `message`와 `details`에는 공개 가능한 문구만 넣는다. HTTP 예외는 내부 `detail`을 숨기고 기본 안전 문구로 변환하며 `WWW-Authenticate`, `Retry-After` 등의 헤더를 보존한다.

예상하지 못한 예외와 응답 모델 검증 실패는 HTTP 500으로 변환한다. 로그에는 예외 클래스 이름만 기록하며 원본 예외 문구·입력·자격 증명을 기록하지 않는다. 오류 경계는 CORS 안쪽에 등록하여 브라우저가 500 오류 본문도 읽을 수 있게 한다. 응답 전송이 시작된 스트리밍 오류나 프록시·네트워크 오류까지 JSON으로 변환하지는 않는다.

`FastAPI(responses=ERROR_RESPONSES)`가 공통 오류 스키마를 OpenAPI에 등록한다. 새 라우트가 자체 `responses`를 지정하면 해당 오류 응답에도 `ApiFailure` 모델을 사용한다.

현재 `/api/v1/health`와 `/api/v1/health/db`가 성공 래퍼를 사용한다. DB RPC 호출 실패 또는 `true`가 아닌 결과는 HTTP 503과 `SERVICE_UNAVAILABLE`을 반환한다.

## 프론트엔드 적용

[api-types.ts](../../frontend/src/lib/api-types.ts)의 `ApiResponse<T>`는 `success`로 성공·실패를 구분하는 유니온이다. [api.ts](../../frontend/src/lib/api.ts)의 `apiFetch<T>()`는 공통 구조를 검사하고 성공 시 `data`를 반환한다.

```ts
import { apiFetch, ApiRequestError } from "@/lib/api";
import type { DatabaseHealthData } from "@/lib/api-types";

try {
  const health = await apiFetch<DatabaseHealthData>("/api/v1/health/db");
  console.log(health.database);
} catch (error) {
  if (error instanceof ApiRequestError) {
    // error.status, error.code, error.message, error.details로 처리한다.
  } else {
    throw error;
  }
}
```

| 상황 | 처리 |
| --- | --- |
| 정상 성공 응답 | `Promise<T>`로 `data` 반환 |
| 정상 서버 오류 응답 | HTTP 상태·서버 코드·필드 오류를 가진 `ApiRequestError` |
| fetch 연결 실패 | `NETWORK_ERROR`, `status: null` |
| JSON 파싱 실패·구조 오류·HTTP 상태와 `success` 불일치·빈 204 | `INVALID_RESPONSE`, 실제 HTTP 상태 유지 |
| 요청 또는 본문 읽기 중 `AbortError` | 원래 취소 예외 유지 |

타입 인자 `T`는 개별 데이터의 런타임 검증을 수행하지 않는다. 공통 래퍼와 오류 상세 구조만 검사하며 API별 데이터 검증이 필요한 곳에서는 별도 검증을 추가한다. 일반 API 주소·단일 `/` 경로 검사·`cache: "no-store"` 동작을 유지한다. `/api/v1/auth/` 경로는 같은 출처의 Next.js 중계 경로와 `credentials: same-origin`을 사용한다.

## 변경과 검증

기존 health API의 `status`는 이제 `data.status`에 있다. `apiFetch`는 원본 `Response` 대신 데이터를 반환하므로 호출부에서 `.json()`을 다시 호출하지 않는다. 응답 계약을 변경할 때는 프론트와 백엔드를 함께 적용하고 외부 소비자가 있다면 호환성을 먼저 확인한다.

저장소 루트에서 실행한다. 백엔드는 프로젝트 의존성이 설치된 Python을 사용한다. 테스트는 실제 환경 파일을 로드하지 않고 외부 DB 호출을 대체한다.

```sh
PYTHONPATH=backend python -m unittest discover -s backend/tests -p test_api_responses.py -v
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
```

프론트 테스트는 TypeScript 직접 실행을 지원하는 Node.js 24를 사용한다. 백엔드 테스트는 정상 200·DB 실패 503·입력 실패 422·HTTP 401 헤더·404·안전한 500·500 CORS·OpenAPI를 검증한다. 프론트 테스트는 성공 데이터, 서버 오류, 잘못된 응답, 네트워크 실패, 취소와 경로 검사를 검증한다. 모의 DB 테스트는 실제 Supabase 연결이나 배포 환경 검증을 대신하지 않는다.

[문서 목록](../README.md)
