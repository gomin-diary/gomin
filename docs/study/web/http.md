# HTTP와 요청·응답

브라우저와 서버는 서로 약속한 형식으로 메시지를 주고받는다. 웹에서 널리 사용하는 통신 규칙이 HTTP다. 클라이언트가 요청을 보내면 서버가 응답한다.

## URL을 읽는 법

다음 주소는 설명용 예시다.

```text
https://api.example.com:443/articles?limit=10#recent
```

| 부분 | 뜻 |
| --- | --- |
| `https` | 통신 방식. HTTPS는 TLS로 HTTP 통신을 보호한다. |
| `api.example.com` | 접속할 호스트 이름 |
| `443` | 접속할 포트. HTTPS의 기본 포트라 생략할 수 있다. |
| `/articles` | 서버에 요청하는 경로 |
| `?limit=10` | 추가 조건을 전달하는 쿼리 문자열 |
| `#recent` | 문서 안의 위치 등을 가리키는 조각 식별자. HTTP 요청에는 보내지 않는다. |

포트는 한 컴퓨터에서 어떤 프로그램에 연결할지 구분하는 번호다. 로컬에서 화면 서버와 API 서버를 다른 포트로 실행하는 이유도 여기에 있다. DNS는 호스트 이름으로 접속할 주소를 찾는 데 사용한다. 브라우저나 운영체제가 이전 조회 결과를 재사용하기도 한다.

## 요청에는 무엇이 들어갈까

HTTP 요청의 의미를 알아보기 쉬운 텍스트로 표현하면 다음과 같다.

```http
GET /api/v1/health HTTP/1.1
Host: api.example.com
Accept: application/json
```

`GET`은 요청 메서드다. 조회, 생성, 수정처럼 어떤 처리를 요청하는지 나타낸다. 경로는 그 처리를 요청할 대상을 가리킨다. `Host`, `Accept` 같은 헤더에는 대상 호스트나 원하는 응답 형식 등 부가 정보를 담는다.

본문은 실제로 전달할 데이터다. 회원가입 요청이라면 이름·이메일 같은 입력값을 JSON 본문에 담을 수 있다. 모든 요청에 본문이 있는 것은 아니다. 메서드별 의미는 [REST API](../api/rest-api.md)에서 더 살펴본다.

## 응답에는 무엇이 들어갈까

우리 프로젝트의 상태 확인 API를 예로 들면 다음과 같다. 전송 형식을 설명하려고 필요한 부분만 표시했다.

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"success":true,"data":{"status":"ok"},"error":null}
```

상태 코드 `200`은 요청을 정상적으로 처리했다는 뜻이다. `Content-Type`은 본문 형식을 알려준다. 위 본문은 JSON이며 `success`, `data`, `error`는 우리 프로젝트가 정한 필드다. HTTP 자체가 요구하는 필드는 아니다.

JSON은 데이터를 문자열로 표현하는 형식이다. 객체, 배열, 문자열, 숫자, `true`, `false`, `null`을 사용한다. 자바스크립트 객체와 모양이 비슷하지만 JSON의 키와 문자열은 큰따옴표로 감싸며 주석을 넣지 않는다.

## 상태 코드를 읽는 법

| 코드 | 흔히 만나는 의미 |
| --- | --- |
| `200` | 요청 처리 성공 |
| `201` | 새 리소스 생성 |
| `204` | 처리 성공, 응답 본문 없음 |
| `301`, `302` | 다른 주소로 이동 안내 |
| `400` | 잘못된 요청 |
| `401` | 유효한 인증 정보가 필요함 |
| `403` | 요청한 작업을 허용하지 않음 |
| `404` | 요청한 대상을 찾지 못함 |
| `422` | 본문을 이해했지만 입력 내용을 처리할 수 없음. 우리 API에서는 입력 검증 실패 등에 사용 |
| `500` | 서버 내부 오류 |
| `503` | 현재 서비스를 제공하기 어려움 |

상태 코드는 출발점이다. 정확한 원인은 응답 본문이나 서버 로그를 함께 살펴야 한다. 서버에 연결하지 못한 경우에는 HTTP 응답 자체가 없을 수도 있다.

## HTTPS가 보호하는 범위

HTTPS는 통신 내용을 암호화하고 접속한 서버의 신원을 인증서로 확인한다. 주소가 HTTPS라는 사실만으로 서비스의 모든 입력 검사와 권한 처리가 올바르다고 판단할 수는 없다.

HTTP는 각 요청을 독립적으로 처리하는 규칙이다. 로그인 상태를 이어가려면 쿠키와 세션 같은 별도 장치가 필요하다. 이 내용은 [인증과 인가](../application/authentication.md)에서 다룬다.

## 우리 프로젝트에서는

`GET /api/v1/health`는 API 서버의 응답을 확인한다. `GET /api/v1/health/db`는 DB 함수 호출까지 확인하며 DB 확인이 실패하면 `503`을 반환한다.

프론트엔드의 [apiFetch](../../../frontend/src/lib/api.ts)는 HTTP 상태와 공통 JSON 응답을 함께 확인한다. 자세한 응답 형식은 [공통 API 응답 모델](../../engineering/api-response.md)에 정리되어 있다.

## 이어서 읽기

- [API란 무엇일까](../api/api-basics.md)

## 참고 자료

- [MDN: HTTP 개요](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview)
- [MDN: URL이란 무엇일까](https://developer.mozilla.org/en-US/docs/Learn_web_development/Howto/Web_mechanics/What_is_a_URL)
- [HTTP 의미와 상태 코드 표준](https://www.rfc-editor.org/rfc/rfc9110.html)

[목차](../README.md)
