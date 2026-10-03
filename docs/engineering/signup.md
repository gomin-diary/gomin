# 이메일 인증·회원가입 구현

기준은 [GOMIN-15](https://younkim.atlassian.net/browse/GOMIN-15),
[GOMIN-21](https://younkim.atlassian.net/browse/GOMIN-21),
[GOMIN-22](https://younkim.atlassian.net/browse/GOMIN-22)와
[기본 인증 ERD](https://younkim.atlassian.net/wiki/spaces/GOMIN/pages/1572868)다.
FastAPI가 인증하며 Supabase Auth는 사용하지 않는다.

## 가입 흐름과 API

모든 인증 API는 [공통 응답 계약](api-response.md)을 사용한다.
프론트엔드는 `apiFetch`로 동일 출처 `/api/v1/auth/...`를 호출하고 Next.js가
`NEXT_PUBLIC_API_BASE_URL`의 FastAPI로 전달한다. 프록시는 `gomin_session` 쿠키만
전달하며 응답의 Set-Cookie를 프론트엔드 출처로 돌려준다. 운영에서 Vercel과 Render의
서로 다른 도메인 사이에 직접 쿠키를 전달하지 않아도 `SameSite=Lax`가 적용된다.

| API | 입력 | 결과 |
| --- | --- | --- |
| `POST /api/v1/auth/email-verifications` | `email` | 요청 UUID, 코드 만료 시각 |
| `POST /api/v1/auth/email-verifications/confirm` | `email`, `verification_id`, 6자리 `code` | 일회용 가입 증표, 증표 만료 시각 |
| `POST /api/v1/auth/signup` | `name`, `email`, `password`, `confirmation`, `verification_proof`, `consents` | HTTP 201, 회원 정보, 초기 세션 쿠키 |
| `GET /api/v1/auth/me` | 세션 쿠키 | 현재 회원 정보, 만료 갱신 |
| `POST /api/v1/auth/logout` | 세션 쿠키 | 현재 세션 삭제 및 쿠키 제거 |

`consents`는 `terms_of_service`와 `privacy_collection` 두 객체다. 각 객체는
`type`, `version`, `agreed: true`를 가지며 하나라도 빠지거나 버전이 다르면 거부한다.

이메일은 앞뒤 공백 제거·소문자 정규화, 이름은 앞뒤 공백 제거 후 1~30자로 검증한다.
비밀번호는 최소 8자와 확인 일치를 검증하고 공백을 보존한다. 요청 자원 보호를 위한
비밀번호 입력 상한은 1,024자다. 해시는 scrypt(N=32768, r=8, p=3)과 무작위 salt를
사용한다. [OWASP 비밀번호 저장 기준](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)을 참고했다.

세션 쿠키는 `app.auth.session.set_session_cookie`로 발급하고, 현재 사용자 조회·로그아웃은 공통 `sessions.py`에서 처리한다.

## 데이터와 원자성

[공통 인증·DB 기반](auth-foundation.md)의 `20261002000000_login_sessions.sql`은 `members`, `auth_sessions`와
세션 생성·갱신 RPC를 제공한다. `20261002010000_signup_verification.sql`은
`member_consents`, `email_verifications` 및 가입 RPC를 추가한다. 모든 인증 테이블에
RLS를 적용하고 Data API 권한과 RPC 실행을 서버의 `service_role`로 제한한다.

코드는 UUID·이메일·가입 목적·서버 키를 묶은 HMAC만 저장한다.
메일 접수 후 코드가 3분간 유효해지고, 확인 성공 시 코드 HMAC을 삭제하고
30분 유효한 증표 digest로 교체한다. 새 요청은 이전 pending·sent·verified 내역을
무효화하며 늦은 메일 응답은 무효화한 내역을 되살리지 않는다.
메일 접수 성공·확인된 실패·접수 불명확 결과를 구분한다. 불명확 결과는 pending을 유지하며
사용자는 새 코드를 요청할 수 있다. 자동 재시도나 원래 코드 복구는 제공하지 않는다.

동일 이메일의 요청은 트랜잭션 advisory lock을 공유한다. 코드 확인과 가입은 행 잠금으로
일회성을 보장한다. 가입 RPC는 회원·두 동의·초기 세션 생성과 증표 소비를 한 트랜잭션으로
수행하며 이메일 UNIQUE로 중복 생성을 차단한다. 실패 시 부분 회원이나 동의가 남지 않는다.
세션 원문은 HttpOnly 쿠키로만 반환하고 digest만 저장한다. 유효한 현재 사용자 조회는
만료를 현재 시각+7일로 갱신하며 삭제·만료된 세션을 다시 생성하지 않는다.

## 설정과 약관

`backend/.env.example`을 기준으로 서버 설정을 등록한다.

- `AUTH_HMAC_KEY`: 독립적으로 생성한 서버 전용 난수 키, 최소 32바이트. 미설정이면 이메일 인증을 HTTP 503으로 거부한다. 실제 키는 코드·문서·Jira에 넣지 않는다.
- `AUTH_COOKIE_SECURE`: 기본 true. 로컬 HTTP에만 false를 사용한다.
- `AUTH_TERMS_VERSION`, `AUTH_PRIVACY_VERSION`: 기본 `dev-2026-10-02`.
- 메일 설정은 [메일 발송](email-delivery.md), 배포는 [배포 안내](../deployment/README.md)를 따른다.

사용자 허용에 따라 `frontend/src/content/legal.ts`에 두 개발용 초안을 작성했다.
`/terms`, `/privacy`에서 전문과 버전을 열람하고 가입 화면에서 각각 동의한다.
운영 적용 시 전문과 버전, 서버 설정을 함께 갱신한다. 초안 문구는 운영 주체·보유 기간·문의처가
확정되지 않았음을 표시하며 확정된 운영 약관으로 취급하지 않는다.

[GOMIN-54~57 후속 정책](https://younkim.atlassian.net/wiki/spaces/GOMIN/pages/1867777)은
이번 구현에 포함하지 않는다. 실패 횟수·재발송 대기·발송량 제한, 허용 도메인과 추가
비밀번호 조합은 해당 후속 작업에서 적용한다. 소셜 인증·재설정·탈퇴도 별도 범위다.

## 로컬 데이터와 검증

회원가입 변경과 함께 [로컬 계정 세 개](../local-development/test-users.md)를 seed로 제공한다.
운영 마이그레이션에 테스트 계정을 넣지 않으며 기존 같은 이메일 회원은 덮어쓰지 않는다.

```sh
PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests -v
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

SQL 검증용 PGlite는 앱 의존성이 아닌 임시 테스트 의존성이다. 다음 명령은 실제 환경 파일이나
Supabase 자격증명을 읽지 않고 임시 PostgreSQL 런타임에 마이그레이션과 seed를 적용한다.

```sh
npm install --prefix /tmp/gomin-signup-db-test @electric-sql/pglite
PGLITE_MODULE=/tmp/gomin-signup-db-test/node_modules/@electric-sql/pglite/dist/index.js node --test supabase/tests/signup.test.mjs
```

2026-10-02 검증: 백엔드 60개, SQL 8개, 프론트 API·프록시 12개 테스트와 린트·타입·빌드 통과.
SQL 검증은 만료·변조·이메일 연결·재사용 거부, 재발급 무효화·늦은 응답,
트랜잭션 롤백, 세션 만료·삭제, 접근 권한과 seed 반복 적용·기존 계정 보존을 포함한다.
실제 FastAPI와 Next.js를 임시 PostgreSQL 어댑터·테스트 메일 발송기에 연결해 브라우저 가입 후
홈 이동과 중복 이메일 안내를 확인했다. HTTP 통합 검증은 가입 쿠키로 현재 사용자 조회·로그아웃,
소비한 증표 재사용 거부와 더미 계정 3개의 로그인까지 통과했다. 화면은 PC 기본 뷰포트, 390×844, 320×568에서
가로 넘침·입력·개별 동의·오류 안내를 확인했다.

실제 로컬 Supabase·Cloud 적용, Resend 실제 메일 수신, 여러 DB 연결 사이의 동시 경합,
운영 HTTPS 및 실제 모바일 기기는 미검증이다. PGlite의 단일 연결 테스트는 다중 연결
행 잠금 경합을 대체하지 않는다.

[문서 목록](../README.md)
