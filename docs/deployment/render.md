# Render — FastAPI·Uvicorn

`backend/`의 FastAPI 애플리케이션을 Uvicorn으로 실행한다. 운영 배포 브랜치·자동 배포 트리거·서비스 도메인은 해당 Render Web Service 설정에서 확인한다.

## 실행과 연결 설정

Render의 Environment에 다음 값을 등록합니다. 프로젝트 URL과 Secret 키는 해당 Supabase Cloud 프로젝트의 Connect/API Keys 화면에서 확인합니다.

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY=<Supabase Cloud의 Secret 키>
CORS_ORIGINS=["https://<프론트엔드 도메인>"]
AUTH_COOKIE_SECURE=true
```

DB 비밀번호나 `DATABASE_URL`은 백엔드 실행에 필요하지 않습니다. Secret 키는 서버 전용이며 프론트엔드 환경 변수에 넣지 않습니다. 이 키는 Supabase 계정용 Personal Access Token과 다릅니다.

Render의 Root Directory는 `backend`, Build Command는 `pip install -r requirements.txt`, Start Command는 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`로 지정합니다. Python 3.12 이상을 사용합니다. `backend/.python-version`의 `3.12`는 배포 기본 버전이며 최소 버전 제한과는 별개입니다. 다른 버전으로 배포하려면 해당 파일도 맞춰 변경하세요.

그림일기 생성에는 Copa 텍스트용 `AI_API_KEY`와 Gemini 이미지용 `GEMINI_API_KEY`를 등록한다.
모리 참조 이미지는 `backend/app/assets/mori.png`에 포함되어 프론트엔드 파일이나 공개 URL 조회 없이 사용한다.
이미지 교체 시 원본·백엔드 복사본을 함께 갱신하는 기준과 제공자 설정은 [그림일기 MVP](../engineering/diary-mvp.md)를 따른다.

Supabase Cloud에서 Data API를 활성화하고 `public` 스키마를 노출해야 합니다. 배포 전 마이그레이션 워크플로로 `supabase/migrations/`의 미적용 SQL을 해당 프로젝트에 적용합니다. 애플리케이션은 시작할 때 스키마를 변경하지 않습니다.

DB 연결과 마이그레이션 적용 기준은 [Supabase DB 운영](supabase-database.md), 버킷·파일 크기 설정은 [Supabase Storage 운영](supabase-storage.md)을 따른다. DB 변경이 필요한 릴리스에서는 운영 마이그레이션 성공 후 백엔드를 배포하도록 자동 배포 트리거와 실행 순서를 맞춘다.

실행 방식은 [Render FastAPI 배포 안내](https://render.com/docs/deploy-fastapi)를 참고한다.

## 회원가입 인증 설정

이메일 인증에 서버 전용 `AUTH_HMAC_KEY`(최소 32바이트의 독립 난수 키)가 필요하다.
운영 HTTPS에서는 `AUTH_COOKIE_SECURE=true`를 사용한다. 약관 전문·프론트 버전과 서버의
`AUTH_TERMS_VERSION`, `AUTH_PRIVACY_VERSION`을 함께 관리한다. 현재 기본 버전은 개발용
초안 `dev-2026-10-02`이며 운영 적용 전에 전문·버전을 확정한다. 인증 API는 브라우저에서
백엔드로 직접 호출하며 HttpOnly·SameSite=Lax 쿠키를 API 호스트에 설정한다.
프론트와 API는 같은 상위 도메인의 HTTPS 주소를 사용하며 쿠키 포함 CORS 요청을 허용한다.

`20261002000000_login_sessions.sql`, `20261002010000_signup_verification.sql`도
Supabase Cloud에 적용해야 한다. `supabase/seed.sql`의 로컬 테스트 계정은 운영에 적용하지 않는다.
API·데이터 동작과 검증 범위는 [회원가입 구현](../engineering/signup.md)을 따른다.

## Google OAuth 설정

| 설정 이름 | 설명 |
| --- | --- |
| `GOOGLE_OAUTH_CLIENT_ID` | Google Cloud 웹 애플리케이션 클라이언트 ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | 백엔드 전용 클라이언트 비밀값 |
| `GOOGLE_OAUTH_REDIRECT_URI` | 실제 API HTTPS 출처 + `/api/v1/auth/google/callback`. Google Cloud 등록 URI와 일치 |
| `AUTH_FRONTEND_ORIGIN` | 실제 프론트 HTTPS 출처. 경로 없이 설정 |
| `AUTH_OAUTH_ENCRYPTION_KEY` | `Fernet.generate_key()`로 생성한 독립 백엔드 키 |
| `AUTH_COOKIE_SECURE` | `true` |
| `CORS_ORIGINS` | `AUTH_FRONTEND_ORIGIN`을 포함하는 프론트 출처 목록 |
| `NEXT_PUBLIC_API_BASE_URL` | Vercel에 등록할 실제 API HTTPS 출처 |

- **쿠키:** 같은 상위 도메인의 HTTPS 프론트·API 사용.
- **Google Cloud:** 동의 화면과 웹 클라이언트 설정. 테스트 상태이면 테스트 사용자 등록.
- **DB:** 기존 인증 마이그레이션 후 `20261004102555_google_oauth.sql`, `20261004110048_google_oauth_completion.sql` 순서로 적용.
- **로그:** 프록시·호스팅 access log에서 OAuth 콜백 쿼리 제외.
- **확인:** 신규 가입·동일 이메일 자동 연결·기존 Google 로그인·취소·me 조회·로그아웃.
- **관리:** [Google OAuth 흐름 관리](../engineering/google-oauth-flow.md)의 상태 수명·정리 기준 적용.

## 인증 메일 발송 설정

Render Free 웹 서비스는 SMTP용 25·465·587번 포트의 outbound 연결을 차단하므로
메일 발송에 Resend HTTPS API를 사용한다.
[Render Free 제한](https://render.com/docs/free#other-limitations)을 참고한다.
SMTP 연결이 가능한 환경에서는 `MAIL_PROVIDER=smtp`로 기존 SMTP 구현을 선택할 수 있다.

Resend API 키는 발송 요청 인증에, 발신 도메인 검증은 해당 도메인을 소유하고
발신 주소로 사용할 수 있음을 확인하는 데 필요하다. Render에는 백엔드가 실행될 때
이 값을 읽을 수 있도록 환경변수를 등록한다.
[Resend API 인증](https://resend.com/docs/api-reference/introduction)과
[발신 도메인 안내](https://resend.com/docs/dashboard/domains/introduction)를 참고한다.

1. Resend에 소유한 발신 도메인 또는 발송용 하위 도메인을 추가한다.
2. Resend가 제시하는 DNS 레코드를 DNS 관리 화면에 등록하고 도메인 검증 완료를 확인한다.
3. 메일 발송 권한이 있는 API 키를 발급하고 검증된 도메인의 발신 주소를 정한다.
4. Render 백엔드의 Environment에 다음 설정을 등록하고 재배포한다.

   ```dotenv
   MAIL_PROVIDER=resend
   RESEND_API_KEY=<Resend API 키>
   RESEND_FROM_EMAIL=<검증된 도메인의 발신 주소>
   RESEND_FROM_NAME=Gomin
   RESEND_TIMEOUT_SECONDS=10
   ```

5. 통제된 테스트 수신함으로 발송해 API 접수 ID와 실제 수신을 확인한다.

실제 API 키는 서버 전용으로 관리한다. 상태 API 성공만으로 메일 설정이나 실제 수신이
검증되지는 않는다. 설정 항목의 기본값과 모듈 호출·오류 처리는
[SMTP·Resend 이메일 발송](../engineering/email-delivery.md)을 따른다.

## 배포 후 확인

- `GET /api/v1/health`의 HTTP 200과 `data.status: "ok"`를 확인한다.
- `GET /api/v1/health/db`의 HTTP 200과 `data.database: "connected"`를 확인한다. DB 상태 확인 실패는 [DB 운영 문서](supabase-database.md#운영-확인)를 따른다.
- 프론트엔드의 실제 Origin에 대한 CORS 허용과 HTTPS 세션 쿠키, 로그인·로그아웃을 확인한다.
- 인증 메일은 제공자 접수 결과와 실제 수신을 함께 확인한다. 상태 API 성공만으로 메일 설정을 검증하지 않는다.
- Uvicorn 시작 실패나 런타임 오류는 Render 배포 로그에서 확인하고 실제 비밀값·OAuth 콜백 쿼리를 공유하지 않는다.

[UptimeRobot 모니터링](uptimerobot.md) · [배포·운영 개요](README.md) · [문서 목록](../README.md)
