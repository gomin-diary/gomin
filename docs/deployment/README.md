# Vercel / Render / Supabase Cloud 배포

프론트엔드, 백엔드, 데이터베이스의 배포 설정을 설명한다. 서비스에 등록된 자동 배포 트리거와 대상 브랜치는 각 서비스의 프로젝트 설정에서 확인한다.

## 프론트엔드 — Vercel

Frontend는 `frontend/`의 Next.js 애플리케이션입니다. `frontend/package.json`에 `build`, `start`, `lint`, `typecheck` 명령이 정의되어 있습니다. 공통 API 함수는 `NEXT_PUBLIC_API_BASE_URL`을 사용하며, 배포 시 Render API 주소를 설정합니다. `frontend/.env.example`의 루프백 주소는 로컬 개발용입니다. 서버 Secret 키를 `NEXT_PUBLIC_` 변수에 넣지 않습니다.

## 백엔드 — Render와 Supabase Cloud

Render의 Environment에 다음 값을 등록합니다. 프로젝트 URL과 Secret 키는 해당 Supabase Cloud 프로젝트의 Connect/API Keys 화면에서 확인합니다.

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY=<Supabase Cloud의 Secret 키>
CORS_ORIGINS=["https://<프론트엔드 도메인>"]
AUTH_COOKIE_SECURE=true
```

DB 비밀번호나 `DATABASE_URL`은 백엔드 실행에 필요하지 않습니다. Secret 키는 서버 전용이며 프론트엔드 환경 변수에 넣지 않습니다. 이 키는 Supabase 계정용 Personal Access Token과 다릅니다.

Render의 Root Directory는 `backend`, Build Command는 `pip install -r requirements.txt`, Start Command는 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`로 지정합니다. Python 3.12 이상을 사용합니다. `backend/.python-version`의 `3.12`는 배포 기본 버전이며 최소 버전 제한과는 별개입니다. 다른 버전으로 배포하려면 해당 파일도 맞춰 변경하세요.

Supabase Cloud에서 Data API를 활성화하고 `public` 스키마를 노출해야 합니다. 배포 전 `supabase/migrations/`의 SQL을 해당 프로젝트에 적용합니다. 현재 상태 확인 함수는 Supabase SQL Editor에서 `20260929000000_health_check.sql` 내용을 실행하면 추가할 수 있습니다. 애플리케이션은 시작할 때 스키마를 변경하지 않습니다.

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

1. 프론트엔드 주소에서 페이지와 정적 파일이 정상적으로 열리는지 확인한다.
2. 백엔드의 `GET /api/v1/health`가 HTTP 200과 `status: ok`를 반환하는지 확인한다.
3. `GET /api/v1/health/db`가 HTTP 200과 `database: connected`를 반환하는지 확인한다. HTTP 503이면 Supabase 설정과 마이그레이션 적용 여부를 확인한다.
4. 배포된 프론트엔드 출처에서 API 요청을 보내 CORS 허용 여부와 API 주소 설정을 확인한다. 홈은 현재 사용자 API를 호출하지만 페이지 표시만으로 DB 연결 성공을 판단하지 않는다.
5. 인증 API는 같은 출처의 Next.js 경로를 통해 중계한다. 운영 HTTPS에서 Secure·HttpOnly·SameSite=Lax 쿠키와 로그인·새로고침·로그아웃을 확인한다. [로그인과 세션](../engineering/login-auth.md)을 따른다.

배포 전 코드 검사는 [코딩과 검증 규칙](../engineering/coding-conventions.md)을 따른다.

[문서 목록](../README.md)
