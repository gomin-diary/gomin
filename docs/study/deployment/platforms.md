# 배포 플랫폼의 역할

Next.js, FastAPI, Uvicorn은 애플리케이션을 만드는 데 사용하는 기술이다. Vercel과 Render는 그 애플리케이션을 외부에 제공하는 플랫폼이다. Supabase는 데이터베이스와 파일 저장소 등을 제공한다.

도구의 이름을 외우기보다 “어떤 프로그램이 어디서 실행되고 누구와 통신하는가”를 보면 구성이 이해하기 쉽다.

## 현재 사용하는 구성

| 영역 | 사용하는 기술·서비스 | 맡는 일 |
| --- | --- | --- |
| 화면 구현 | React·Next.js | 화면, 페이지 경로, 렌더링 구성 |
| 프론트 배포 | Vercel | Next.js 빌드와 웹 제공 |
| API 구현 | FastAPI | 요청 검증과 업무 처리, 응답 생성 |
| API 서버 실행 | Uvicorn | FastAPI 앱과 외부 HTTP 요청 연결 |
| 백엔드 배포 | Render | Python 의존성 설치와 API 서버 실행 |
| DB | Supabase PostgreSQL | 회원·세션 등의 데이터 저장 |
| 데이터 접근 | Supabase Data API | 백엔드의 DB 조회·함수 호출 연결 |
| 파일 저장 | Supabase Storage | 파일 객체 저장과 제공 |
| 외부 상태 확인 | UptimeRobot | 설정한 대상에 요청을 보내 상태 검사 |

UptimeRobot의 감시 대상과 검사 주기·알림 설정은 서비스 대시보드에서 확인한다.

## Vercel에서 하는 일

Vercel은 Next.js 프로젝트를 빌드하고 생성한 페이지·파일과 필요한 서버 기능을 제공한다. 정적 파일을 여러 지역에서 전달하는 CDN 같은 기능도 지원한다. CDN은 파일 복사본을 사용자와 가까운 위치에서 제공해 전달 시간을 줄이는 네트워크다.

우리 프로젝트의 프론트 작업 폴더는 `frontend`다. 다만 문서 원본은 루트 `docs/`에 있으므로 빌드에서 그 폴더도 읽을 수 있어야 한다. Markdown은 빌드 전에 문서 데이터로 바뀌고 공개 문서 페이지에 포함된다.

`frontend/vercel.json`은 `main` 브랜치만 Git 자동 배포를 허용한다. 이때 프론트·문서·루트 README 변경을 빌드 대상으로 포함한다. PR에서는 GitHub Actions가 빌드를 검사한다. 운영 브랜치와 도메인 등은 Vercel 프로젝트 설정도 함께 확인한다.

## Render에서 하는 일

Render는 백엔드 작업 폴더의 의존성을 설치하고 서버 프로그램을 시작한다. 우리 [Render 배포 안내](../../deployment/render.md)는 작업 폴더를 `backend`로 지정하고 다음 형태의 실행 명령을 사용한다.

```sh
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

`app.main:app`은 실행할 앱, `--host`는 요청을 받을 네트워크 인터페이스, `--port`는 포트다. `0.0.0.0`은 모든 IPv4 인터페이스에서 요청을 받는다는 뜻이며 브라우저에 입력할 공개 도메인은 아니다. `$PORT`는 Render가 전달한 환경변수 값을 사용한다.

화면의 공개 API 주소는 Render 백엔드 주소를 가리켜야 한다. 브라우저가 API를 직접 호출하므로 백엔드 CORS와 세션 쿠키 설정도 함께 맞춘다.

## Supabase에서 하는 일

백엔드는 서버 전용 인증 정보로 Supabase Data API와 Storage를 사용한다. Data API는 PostgreSQL에 저장한 데이터와 DB 함수를 호출하는 경로다. Storage는 파일 저장을 담당한다.

Supabase가 제공하는 Auth를 우리 로그인에 사용하지는 않는다. 로그인 처리와 세션 검증은 FastAPI가 맡고 필요한 데이터를 Supabase DB에 저장한다.

DB 마이그레이션은 앱 배포와 별도로 적용한다. 로컬 DB와 운영 DB는 설정과 데이터가 다르므로 어느 대상에 변경을 적용하는지도 구분한다.

## 서비스 사이의 연결을 읽는 법

화면이 열리지 않으면 프론트의 배포 상태·도메인·응답부터 살펴본다. 화면은 열리지만 API에 연결하지 못하면 요청 주소와 Render의 상태를 확인한다. API가 DB 오류를 반환하면 Supabase 연결과 해당 함수·권한을 확인한다.

이 순서는 문제 범위를 좁히는 출발점이다. 오류 하나가 반드시 특정 플랫폼의 장애를 뜻하지는 않는다. 잘못된 환경 설정이나 앱 코드도 비슷한 증상을 만들 수 있다.

## 이어서 읽기

- [배포의 기본 개념](deployment-basics.md)
- [모니터링과 UptimeRobot](../operations/monitoring.md)
- [프로젝트 배포 안내](../../deployment/README.md): 설정값과 실제 적용 절차

## 참고 자료

- [Vercel: Next.js 배포](https://vercel.com/docs/frameworks/full-stack/nextjs)
- [Render: FastAPI 배포](https://render.com/docs/deploy-fastapi)
- [Supabase: 데이터베이스](https://supabase.com/docs/guides/database/overview)

[목차](../README.md)
