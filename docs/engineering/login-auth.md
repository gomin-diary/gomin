# 이메일 로그인과 세션

[GOMIN-16](https://younkim.atlassian.net/browse/GOMIN-16), GOMIN-24~26과
[기본 인증 ERD](https://younkim.atlassian.net/wiki/spaces/GOMIN/pages/1572868)의
로그인 범위를 구현한다. FastAPI가 비밀번호와 세션을 검증하고 Supabase는 저장에만
사용한다. 이번 변경은 `members`, `auth_sessions`만 추가하며 이메일 인증·회원가입,
동의 기록과 로그인 실패 제한은 해당 후속 작업에서 구현한다. 가입된 계정이 아직
없으면 로그인할 수 없다. 기본 계정이나 우회 가입 API는 제공하지 않는다.

## API와 저장

| API | 동작 |
| --- | --- |
| `POST /api/v1/auth/login` | 이메일·비밀번호 검증 후 독립 세션과 사용자 정보 반환 |
| `GET /api/v1/auth/me` | 현재 세션 검증·7일 만료 갱신 후 사용자 정보 반환 |
| `POST /api/v1/auth/logout` | 현재 세션 행과 쿠키 삭제; 다른 세션 유지 |

공통 성공 응답의 사용자 데이터는 `id`, `email`, `name`이다. 토큰은 JSON에 포함하지
않고 `gomin_session` 쿠키로 전달한다. 미가입 이메일·비밀번호 불일치는 HTTP 401,
`INVALID_CREDENTIALS`, “이메일 또는 비밀번호를 확인해 주세요.”로 동일하게 처리한다.
유효하지 않은 세션은 401 `UNAUTHORIZED`, DB 이용 실패는 503이다.

이메일은 앞뒤 공백 제거 후 소문자로 비교한다. 비밀번호 공백은 보존한다.
`app/auth/security.py`의 scrypt는 무작위 16바이트 salt, N=32768, r=8, p=3,
32바이트 해시를 사용하며 알고리즘·파라미터·salt를 함께 저장한다.
[OWASP의 scrypt 설정](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)을 따른다.
회원가입 구현도 같은 `hash_password`를 사용해야 한다. 미가입 이메일에도 더미 해시를
검증하며 비밀번호 계산은 이벤트 루프 밖에서 수행한다.

세션 토큰은 32바이트 난수이며 DB에는 SHA-256 digest만 저장한다. 생성·갱신은 DB
시간을 기준으로 7일을 설정한다. 갱신 RPC는 행 잠금 후 만료를 검사하고 기존 행만
UPDATE한다. 로그아웃과 경합해도 삭제된 세션을 INSERT·UPSERT로 복원하지 않는다.
테이블은 RLS를 켜고 Data API 테이블·함수 권한을 `service_role`에만 부여한다.
보호 API를 추가할 때는 `require_member` 의존성으로 회원을 검사해야 한다.

## 쿠키와 호출 경로

브라우저 → 같은 출처의 Next.js `/api/v1/auth/*` → FastAPI 경로로 전달한다.
`apiFetch`는 인증 경로에 상대 주소와 `credentials: same-origin`을 사용한다.
Next.js는 `NEXT_PUBLIC_API_BASE_URL`을 API 목적지로 사용하며 인증 쿠키와
`Set-Cookie`만 중계한다. 서로 다른 Vercel·Render 도메인에서도 `SameSite=Lax`를
유지할 수 있다. 기존 다른 API는 설정된 API 주소를 직접 호출한다.

쿠키는 HttpOnly·SameSite=Lax·Path=/·Max-Age=604800이다.
`AUTH_COOKIE_SECURE`는 기본 `true`이며 운영 HTTPS에서는 그대로 유지한다.
로컬 HTTP에서만 `false`를 사용한다. 공통 로컬 실행기는 이를 자식 프로세스에
전달하고 `.env.example`에도 로컬 값을 안내한다. 별도 CSRF 처리는 기존 결정대로 보류한다.

## 화면

로그인 폼은 필수 입력, 중복 제출 방지, 요청 중 표시, 서버·연결 오류와 성공 시 이동을
처리한다. 기본 목적지는 홈이며 `next` 값은 `/talk`, `/collection`만 허용한다.
회원가입·소셜 로그인·비밀번호 찾기는 기존 준비 안내를 유지한다.

`AuthProvider`는 페이지 이동·창 포커스·화면 복귀·보이는 화면의 5분 간격마다
현재 사용자를 확인한다. 사용자 정보는 메모리에만 보관한다. 털어놓기·컬렉션은
확인된 로그인 상태에서 표시하고 401이면 로그인 화면으로 이동해 재인증을 안내한다.
연결 오류는 로그아웃으로 단정하지 않고 재시도 화면을 표시한다. 이 클라이언트 화면
가드는 업무 API 권한 검사를 대신하지 않는다. 홈·가이드는 비회원도 이용할 수 있다.

## 적용과 검증

로컬 마이그레이션은 저장소 루트에서 `npm run db:migrate`로 적용한다.
`20261002000000_login_sessions.sql`은 가입 기능이 사용할 회원 테이블과 로그인
세션 테이블·RPC를 추가한다. 실제 환경 파일이나 키 조회 출력은 검증에 사용하지 않는다.

```sh
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm test
```

백엔드 인증 테스트는 모의 저장소로 정규화·동일 실패 안내·안전한 쿠키·독립 세션·갱신·
만료·위조·삭제 후 재사용 거부·로그아웃·DB 실패와 비밀번호 해시를 확인한다.
로컬 모의 API와 프로덕션 빌드의 Next.js 중계를 사용한 브라우저 검증에서 데스크톱·390×844 모바일의 실패 안내·성공 이동·새로고침·보호 화면 복귀·로그아웃·서버 연결 실패 안내를 확인했다. 이 검증은 실제 PostgreSQL 적용·행 잠금 경합·운영 도메인 쿠키 검증을 대신하지 않는다. 로컬 DB가 실행 중이지 않아 마이그레이션은 적용하지 않았다.

[문서 목록](../README.md)
