# CORS와 출처

터미널에서는 API가 응답하는데 브라우저에서는 CORS 오류가 날 수 있다. 브라우저가 다른 출처의 응답을 JavaScript에서 읽도록 허용할지 따로 검사하기 때문이다.

## 출처를 구분하는 기준

출처는 스킴, 호스트, 포트의 조합이다. 스킴은 URL 맨 앞의 `https` 같은 부분이다. 경로는 출처에 포함하지 않는다.

| 두 주소 | 같은 출처인가 |
| --- | --- |
| `https://www.example.com/login`과 `https://www.example.com/guide` | 같다. 경로만 다르다. |
| `https://www.example.com`과 `https://api.example.com` | 다르다. 호스트가 다르다. |
| `http://localhost:3000`과 `http://localhost:8000` | 다르다. 포트가 다르다. |
| `http://example.com`과 `https://example.com` | 다르다. 스킴이 다르다. |

브라우저의 동일 출처 정책은 한 출처의 스크립트가 다른 출처의 데이터에 임의로 접근하지 못하도록 제한한다. 다른 서버의 API를 화면에서 사용하려면 이 제한을 어떻게 허용할지 서버가 알려줘야 한다.

## CORS의 역할

CORS는 Cross-Origin Resource Sharing의 줄임말이다. 서버가 HTTP 헤더로 허용할 출처와 요청 조건을 알리면 브라우저가 그 규칙을 확인한다.

예를 들어 `https://www.example.com`의 화면이 `https://api.example.com`으로 요청하면 서버는 허용한 프론트 출처를 `Access-Control-Allow-Origin` 헤더로 알릴 수 있다. 브라우저는 그 값을 요청을 시작한 출처와 대조한다.

CORS는 브라우저가 적용하는 정책이다. 외부 호출자를 인증하거나 API 권한을 검사하는 수단으로 대신 사용할 수 없다. 터미널이나 다른 서버의 요청은 브라우저와 같은 방식으로 CORS를 검사하지 않는다.

## OPTIONS 요청이 먼저 보이는 이유

브라우저는 일부 요청 전에 실제 요청을 보내도 되는지 미리 확인한다. 이를 사전 요청 또는 프리플라이트라고 부른다. 이때 `OPTIONS` 메서드와 요청하려는 메서드·헤더 정보를 사용한다.

예를 들어 다른 출처로 `Content-Type: application/json`인 POST 요청을 보내면 일반적으로 사전 요청이 발생한다. 서버가 이를 허용하면 브라우저가 본 요청을 보낸다. 모든 요청마다 사전 요청이 생기는 것은 아니며 허용 결과를 일정 시간 재사용할 수도 있다.

사전 요청이 없는 요청은 서버에서 이미 처리했더라도 브라우저가 응답 읽기를 막을 수 있다. CORS 오류가 보인다고 실제 작업도 반드시 취소됐다고 판단하지 않는다.

## 쿠키와 함께 사용할 때

다른 출처의 API에 세션 쿠키를 보내려면 요청 옵션, 서버의 CORS 응답, 쿠키의 전송 조건을 함께 맞춘다.

- 프론트엔드는 `credentials: "include"`로 요청한다.
- 서버는 구체적인 프론트 출처와 `Access-Control-Allow-Credentials: true`를 응답한다.
- 쿠키는 호스트·경로·Secure·SameSite 등의 조건을 충족해야 한다.

쿠키를 포함하는 요청에는 허용 출처를 `*`로 응답할 수 없다. CORS를 맞춰도 쿠키 조건이나 브라우저의 개인정보 보호 정책 때문에 쿠키가 전달되지 않을 수 있다.

## 출처와 사이트는 다른 기준이다

SameSite에서 말하는 사이트는 출처와 구분한다. HTTPS를 사용하는 `www.example.com`과 `api.example.com`은 호스트가 달라 서로 다른 출처다. 두 주소는 같은 등록 가능 도메인인 `example.com`을 사용하므로 같은 사이트에 해당한다. 사이트를 비교할 때는 스킴도 고려한다.

따라서 같은 사이트의 두 출처 사이에서도 CORS 설정이 필요할 수 있다. `SameSite=Lax` 설정만 보고 모든 다른 출처 요청에 쿠키가 차단된다고 생각하면 안 된다.

## 우리 프로젝트에서는

백엔드의 [main.py](../../../backend/app/main.py)는 `CORS_ORIGINS`에 등록한 프론트 출처를 허용하고 쿠키 포함 요청을 지원한다. 허용 목록에는 경로가 아닌 `https://www.example.com` 같은 출처를 등록한다.

프론트엔드의 `apiFetch`는 `/api/v1/` 요청에 `credentials: "include"`를 사용한다. 운영 설정은 같은 상위 도메인의 HTTPS 프론트와 API를 전제로 한다. 로컬에서도 호스트를 모두 `localhost` 또는 모두 `127.0.0.1`로 맞춘다.

문제가 생기면 브라우저 Network에서 사전 요청의 성공 여부, 실제 응답 헤더, 쿠키 전송 여부를 나눠 확인한다. 실제 API 오류와 CORS 오류가 함께 나타날 수도 있다. 구체적인 설정은 [공통 인증·DB 기반](../../engineering/auth-foundation.md)을 따른다.

## 이어서 읽기

- [인증과 인가](authentication.md)
- [배포의 기본 개념](../deployment/deployment-basics.md)

## 참고 자료

- [MDN: 동일 출처 정책](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Same-origin_policy)
- [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)

[목차](../README.md)
