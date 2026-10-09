# 백엔드와 FastAPI·Uvicorn

사용자가 로그인 요청을 보내면 서버는 이메일과 비밀번호를 확인하고 결과를 돌려준다. 백엔드는 이런 요청을 받아 입력을 검증하고 필요한 데이터를 조회하거나 저장한 뒤 응답을 만드는 프로그램이다.

## 요청을 처리하는 순서

백엔드가 요청을 처리하는 과정을 단순하게 나누면 다음과 같다. 실제 검사 순서는 API마다 다르다.

1. 경로와 메서드에 맞는 처리 함수를 찾는다.
2. 입력값과 필요한 인증·권한을 확인한다.
3. 데이터 조회·저장 등 요청한 작업을 수행한다.
4. 결과나 오류를 응답한다.

경로와 메서드를 처리 함수에 연결하는 일을 라우팅이라고 한다. 입력 검증은 값의 자료형, 필수 여부, 허용 범위 등을 확인하는 일이다. “이메일 형식인가”와 “이 회원이 이 작업을 해도 되는가”는 서로 다른 검사다.

## FastAPI와 Uvicorn

FastAPI는 Python으로 HTTP API를 만드는 프레임워크다. 경로 선언, 입력·응답 모델, 의존성 연결, OpenAPI 명세 생성 같은 기능을 제공한다. 프레임워크는 이런 공통 기능과 프로그램의 기본 구조를 준비해 둔 틀이라고 이해하면 된다.

Uvicorn은 네트워크 요청을 받아 Python 웹 애플리케이션에 전달하고 응답을 보내는 서버 프로그램이다. Uvicorn과 FastAPI 앱 사이에서는 ASGI라는 호출 규칙을 사용한다. FastAPI가 처리할 내용을 정의하면 Uvicorn이 그 앱을 실행하고 외부 요청을 연결한다.

Render는 이 프로그램을 배포하고 실행하는 플랫폼이다. FastAPI, Uvicorn, Render를 모두 “서버”라고 부르면 각자의 역할을 구분하기 어려워진다.

## 경로와 함수 연결하기

FastAPI로 `GET /greetings` 요청을 처리하는 코드를 작성하면 다음과 같다.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/greetings")
async def greeting(name: str = "방문자"):
    return {"message": f"{name}님, 안녕하세요."}
```

`@app.get("/greetings")`가 GET 요청과 함수를 연결한다. `name`은 쿼리에서 받는 문자열이며 생략하면 기본값을 사용한다. 반환한 딕셔너리는 JSON 응답으로 변환된다. 실제 프로젝트에서는 여기에 공통 응답 모델 등의 규칙을 적용한다.

Pydantic 모델을 사용하면 요청과 응답의 데이터 모양을 코드로 표현할 수 있다. 예를 들어 필수 문자열이나 숫자의 범위를 선언한다. 형식 검증을 통과했더라도 업무 규칙과 권한 검사는 별도로 필요하다.

## async와 await

데이터베이스나 외부 API의 응답을 기다릴 때는 CPU가 계산하지 않는 시간이 생긴다. 비동기 코드는 이 대기 시간에 다른 작업을 진행하도록 작성하는 방식이다. Python에서는 `async def`로 비동기 함수를 선언하고 `await`로 비동기 작업의 결과를 기다린다.

함수에 `async`를 붙이는 것만으로 모든 처리가 빨라지지는 않는다. 오래 걸리는 계산이나 동기 방식의 입출력은 별도로 다뤄야 한다. 호출하는 라이브러리가 어떤 방식으로 동작하는지도 함께 확인한다.

## 우리 프로젝트에서는

[main.py](../../../backend/app/main.py)가 FastAPI 앱을 만들고 라우터, CORS, 예외 처리를 등록한다. 시작할 때 외부 통신용 클라이언트와 Supabase 클라이언트를 만들고 여러 요청에서 재사용한다. 앱이 종료되면 연결을 정리한다.

`app/api/routes/`에는 API 처리 함수가, `app/schemas/`에는 데이터 모델이 있다. DB 클라이언트와 인증 검사 등 여러 API가 함께 쓰는 기능은 `Depends`로 연결한다. 이런 기능을 필요한 곳에 전달하는 방식을 의존성 주입이라고 부른다.

Render는 배포 안내에 따라 `uvicorn app.main:app`으로 앱을 실행한다. `app.main`은 Python 모듈 경로, 마지막 `app`은 그 모듈 안의 FastAPI 객체 이름이다. 실제 호스트·포트 옵션은 [배포 안내](../../deployment/README.md)를 따른다.

## 오류도 응답의 일부다

잘못된 입력이나 만료된 로그인처럼 예상할 수 있는 실패에는 정해진 오류를 반환한다. 예상하지 못한 내부 오류도 안전한 응답으로 바꾸고 로그를 남긴다. 내부 예외 문구나 비밀값을 그대로 사용자에게 보내지 않는다.

우리 프로젝트의 세부 형식과 예외 처리 방식은 [공통 API 응답 모델](../../engineering/api-response.md)에 정리되어 있다.

## 이어서 읽기

- [데이터베이스와 Supabase](../data/database.md)
- [인증과 인가](authentication.md)

## 참고 자료

- [FastAPI 튜토리얼](https://fastapi.tiangolo.com/tutorial/)
- [FastAPI: 서버 직접 실행](https://fastapi.tiangolo.com/deployment/manually/)
- [Python: 비동기 작업](https://docs.python.org/3/library/asyncio-task.html)

[목차](../README.md)
