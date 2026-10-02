# 공통 인증·DB 기반

GOMIN-14의 공통 기반은 회원·세션·이메일 인증·약관 동의 스키마와 DB 함수,
비밀번호·인증번호 암호화, 세션 검증·쿠키, 동일 출처 인증 프록시를 관리한다.
로그인과 회원가입은 이 기반에 각 기능의 API와 화면을 연결한다.

## 데이터베이스

| 테이블 | 역할 |
| --- | --- |
| `members` | 정규화한 이메일, 이름, 비밀번호 해시 |
| `auth_sessions` | 회원별 독립 세션 digest와 만료 시각 |
| `email_verifications` | 인증번호 HMAC, 일회용 가입 증표 digest와 처리 상태 |
| `member_consents` | 회원별 동의 유형·약관 버전·동의 시각 |

`20261002000000_login_sessions.sql`은 회원·세션과 생성·갱신 함수를,
`20261002010000_signup_verification.sql`은 이메일 인증·동의와 인증·가입 함수를 정의한다.
파일명과 SQL은 기존 로그인·회원가입 구현에서 유지했다. 두 마이그레이션은 이 순서로
적용하며, 기능 PR에서 같은 테이블이나 함수를 다시 생성하지 않는다.

세션은 DB 시간 기준 7일이며 유효한 세션만 기존 행의 만료를 갱신한다.
로그아웃으로 삭제된 행을 갱신 과정에서 다시 생성하지 않는다.
인증번호는 메일 접수 후 3분, 가입 증표는 확인 후 30분간 유효하다.
동일 이메일 요청의 advisory lock과 행 잠금으로 재발급·확인·가입을 조정한다.
가입 함수는 회원·두 동의·초기 세션 생성과 증표 소비를 한 트랜잭션으로 처리한다.
4개 테이블은 RLS를 사용하고 Data API 및 함수 권한을 `service_role`로 제한한다.

## 공통 코드와 API

| 경로 | 역할 |
| --- | --- |
| `backend/app/auth/security.py` | scrypt 비밀번호 해시·검증, 세션 난수·SHA-256 digest |
| `backend/app/auth/crypto.py` | 가입 목적·요청·이메일에 묶인 인증번호 HMAC |
| `backend/app/auth/repository.py` | 회원 조회와 세션 생성·갱신·삭제 |
| `backend/app/auth/session.py` | `require_member`, 쿠키 읽기·발급과 저장소 의존성 |
| `backend/app/api/routes/sessions.py` | 현재 사용자 조회와 현재 기기 로그아웃 |
| `backend/app/schemas/auth.py` | 공통 회원 응답 `MemberData` |
| `frontend/src/components/auth-page.tsx` | 기능별 입력 폼을 받는 공통 인증 화면 |
| `frontend/src/lib/auth-proxy.ts` | 허용한 인증 경로·메서드 중계와 세션 쿠키 전달 |

`GET /api/v1/auth/me`는 유효한 세션의 회원을 반환하고 만료·쿠키를 갱신한다.
`POST /api/v1/auth/logout`은 현재 세션과 쿠키를 제거한다.
보호 API는 `app.auth.session.require_member`를 사용한다.
로그인·회원가입 성공 응답의 쿠키는 같은 모듈의 `set_session_cookie`로 발급한다.

브라우저는 `apiFetch`로 같은 출처의 `/api/v1/auth/*`를 호출한다.
Next.js는 `gomin_session` 쿠키만 FastAPI로 전달하고 `Set-Cookie`를 돌려준다.
쿠키는 HttpOnly·SameSite=Lax·Path=/이며 원문 토큰은 DB에 저장하지 않는다.

## 설정과 검증

`backend/.env.example`에서 공통 설정 이름을 확인한다.
`AUTH_COOKIE_SECURE` 기본값은 true이며 공통 실행기는 로컬 HTTP용으로 false를 전달한다.
`AUTH_HMAC_KEY`, `AUTH_TERMS_VERSION`, `AUTH_PRIVACY_VERSION`은 이메일 인증·가입 API에서 사용한다.

```sh
npm run db:migrate
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
```

SQL 회귀 테스트는 별도의 임시 PGlite 런타임으로 두 마이그레이션을 적용하고 인증 상태 전환,
증표의 만료·일회성, 가입 롤백, 세션 갱신·삭제와 접근 권한을 확인한다.

```sh
npm install --prefix /tmp/gomin-signup-db-test @electric-sql/pglite
PGLITE_MODULE=/tmp/gomin-signup-db-test/node_modules/@electric-sql/pglite/dist/index.js node --test supabase/tests/auth-foundation.test.mjs
```

PGlite 검증은 실제 Supabase 적용이나 여러 DB 연결의 잠금 경합을 확인하지 않는다.
상세 규칙은 [코딩과 검증 규칙](coding-conventions.md)을 따른다.

[문서 목록](../README.md)
