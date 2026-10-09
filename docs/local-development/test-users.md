# 로컬 인증 테스트 계정

[GOMIN-58](https://younkim.atlassian.net/browse/GOMIN-58)의 더미 데이터는
회원가입 구현과 함께 `supabase/seed.sql`에 포함한다. FastAPI 자체 인증의
`members`와 `member_consents`를 사용하며 Supabase Auth 계정은 생성하지 않는다.

| 이메일 | 이름 | 로컬 테스트 비밀번호 |
| --- | --- | --- |
| user1@gomin.today | 로컬 사용자 1 | `GominLocal!2026` |
| user2@gomin.today | 로컬 사용자 2 | `GominLocal!2026` |
| user3@gomin.today | 로컬 사용자 3 | `GominLocal!2026` |

이 비밀번호는 공개된 로컬 테스트 전용 값이다. seed는 운영 DB에 적용하지 않는다.
세 계정에는 서로 다른 salt의 scrypt 해시와 개발용 약관 두 건의
`dev-2026-10-02` 동의 기록을 넣는다. 이메일을 발송하거나 세션을 미리 생성하지 않는다.

## 적용

로컬 Supabase를 실행한 뒤 저장소 루트에서 마이그레이션과 seed를 적용한다.
CLI 의존성이 설치되어 있어야 한다.

```sh
npm run db:migrate
npm run db:seed
```

seed가 포함된 로컬 DB 초기화에도 같은 계정이 생성된다. 초기화는 기존 로컬 데이터를
삭제하므로 계정 추가만 필요할 때는 위 seed 명령을 사용한다.
이미 같은 이메일이 있으면 해당 회원의 이름·비밀번호·동의 이력을 보존하고 건너뛴다.
새로 생성한 회원에만 동의 이력을 추가하므로 반복 실행해도 기존 회원의 동의를 만들거나
덮어쓰지 않는다.

## 그림일기용 더미 요약

이미지 생성 MVP를 테스트할 때 계정 seed와 마이그레이션 적용 후 실행한다.

```sh
npm run db:seed:diary
```

각 테스트 계정에 대화·메시지·요약 한 건을 추가한다. 이미지 생성과 컬렉션 저장은 실제 화면에서 수행한다.
재실행해도 기존 요약과 생성·저장한 결과는 덮어쓰지 않는다. 운영 DB에는 적용하지 않는다.

| 로그인 계정 | 로컬 테스트 화면 |
| --- | --- |
| user1@gomin.today | [기대와 불안 요약](http://127.0.0.1:3000/talk?summary=34000000-0000-4000-8000-000000000001) |
| user2@gomin.today | [기쁨과 관계 요약](http://127.0.0.1:3000/talk?summary=34000000-0000-4000-8000-000000000002) |
| user3@gomin.today | [지친 하루 요약](http://127.0.0.1:3000/talk?summary=34000000-0000-4000-8000-000000000003) |

각 링크는 해당 계정으로 로그인해야 조회할 수 있다. 실제 그림일기 생성에는 백엔드의 Copa 텍스트 구성용 `AI_API_KEY`와 이미지 생성용 `GEMINI_API_KEY` 설정이 필요하다.

## 계정 확인

로그인 기능을 함께 적용한 환경에서 `POST /api/v1/auth/login`과 `GET /api/v1/auth/me`로 각 계정을 확인할 수 있다.
회원가입 화면에서 위 이메일로 인증 요청을 하면 중복 이메일 안내가 표시되고 메일은
발송하지 않는다. 신규 회원가입 검증에는 수신 가능한 다른 이메일을 사용한다.
`gomin.today` 테스트 주소에 이메일 허용 도메인 예외를 추가하지 않는다.

해시 검증은 `backend/tests/test_signup.py`, seed 반복 적용·기존 계정 보존은
`supabase/tests/signup.test.mjs`에서 확인한다. 적용 환경과 실제 확인 범위는
[회원가입 구현 안내](../engineering/signup.md)를 따른다.

[문서 목록](../README.md)
