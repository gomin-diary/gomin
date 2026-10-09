# 데이터베이스와 Supabase

사용자가 브라우저를 닫거나 서버를 다시 시작해도 회원 정보를 유지하려면 데이터를 저장해야 한다. 데이터베이스는 데이터를 저장하고 필요한 조건으로 찾으며 여러 변경을 일관되게 처리하는 시스템이다.

## 테이블, 행, 열

관계형 데이터베이스는 데이터를 테이블로 구성한다. 테이블의 한 행은 회원 한 명처럼 개별 대상을 나타내고 열은 이름이나 가입 시각처럼 대상의 속성을 나타낸다.

회원 두 명을 저장한 테이블을 예로 들면 다음과 같다.

| 회원 식별자 | 이름 | 이메일 |
| --- | --- | --- |
| 회원-1 | 새싹 | sprout@example.com |
| 회원-2 | 나무 | tree@example.com |

스프레드시트와 모양은 비슷하지만 DB에는 값의 자료형, 중복 허용 여부, 테이블 간 관계 같은 규칙을 선언할 수 있다. 이런 데이터 구조와 규칙을 스키마라고 부른다.

## 기본 키와 외래 키

기본 키는 한 행을 고유하게 식별하는 값이다. 이름은 동명이인이 있을 수 있고 바뀔 수도 있어서 보통 별도 식별자를 사용한다. 외래 키는 다른 테이블의 행과 관계를 맺는 값이다.

우리 프로젝트에서는 `members.id`가 회원의 기본 키이고 `auth_sessions.member_id`가 그 회원을 참조한다. 회원 한 명에게 여러 세션이 연결될 수 있다. 각 세션 행에 회원 이름과 이메일을 반복해서 저장하는 대신 회원 식별자로 관계를 맺는다.

`NOT NULL`은 값이 반드시 있어야 한다는 규칙이고 `UNIQUE`는 중복을 제한하는 규칙이다. `CHECK`는 값이 정해진 조건을 만족하는지 확인한다. 이런 제약조건은 여러 프로그램이 DB에 접근해도 저장 규칙을 지키도록 돕는다.

## SQL과 조회

SQL은 관계형 DB에 조회나 변경을 요청하는 언어다. `SELECT`는 조회, `INSERT`는 추가, `UPDATE`는 수정, `DELETE`는 삭제에 사용한다.

최근 가입한 회원의 이름을 최대 다섯 개 조회하는 SQL은 다음과 같다.

```sql
select name
from public.members
order by created_at desc
limit 5;
```

`public`은 테이블을 묶는 스키마의 이름이다. PostgreSQL에서는 데이터 구조를 뜻하는 말 외에 이런 이름 공간도 스키마라고 부른다.

`WHERE`로 조건을 지정하고 `JOIN`으로 관계가 있는 테이블을 함께 조회할 수 있다. 인덱스는 특정 조건의 데이터를 빠르게 찾도록 돕는 별도 자료구조다. 저장 공간과 변경 비용도 들기 때문에 모든 열에 무조건 추가하지 않는다.

## 트랜잭션

회원가입 때 회원 행만 저장하고 약관 동의나 세션 저장에 실패하면 데이터가 어긋날 수 있다. 트랜잭션은 여러 작업을 한 묶음으로 처리해 모두 성공하면 확정하고 실패하면 취소하도록 한다.

변경을 확정하는 일을 커밋, 취소하는 일을 롤백이라고 한다. 이 문맥의 커밋은 DB 변경 확정이며 Git 커밋과 구분한다. 동시에 들어오는 요청이 같은 데이터를 바꿀 때는 잠금이나 격리 규칙도 함께 고려한다.

## PostgreSQL과 Supabase

PostgreSQL은 관계형 데이터베이스 소프트웨어다. Supabase는 PostgreSQL과 데이터 접근 API, Storage 등 여러 기능을 제공하는 플랫폼이다. Supabase를 쓴다고 제공되는 기능을 모두 사용하는 것은 아니다.

우리 백엔드는 Supabase Python SDK로 Data API를 호출한다. Data API가 DB 조회와 SQL 함수 실행을 연결한다. 백엔드가 DB 비밀번호로 PostgreSQL에 직접 접속하는 구조와 구분한다.

RPC는 다른 곳에 있는 함수를 호출하는 방식을 뜻한다. 우리 코드의 `supabase.rpc(...)`는 DB에 정의한 함수를 Data API로 호출한다. 일반적인 SQL 조회와 함수 호출 모두 실제 권한과 입력 조건을 따라야 한다.

## 우리 프로젝트에서는

인증 데이터는 `members`, `auth_sessions`, `email_verifications`, `member_consents` 등에 저장한다. 회원가입 함수는 회원·동의·초기 세션 생성과 가입 증표 소비를 한 트랜잭션으로 처리한다.

인증 테이블에는 RLS와 서버 전용 접근 권한을 적용한다. RLS는 행 단위 접근 규칙을 적용하는 PostgreSQL 기능이다. 실제 접근 가능 범위는 DB 역할과 권한을 함께 살펴야 하며 서버 전용 키를 브라우저에 전달하지 않는다.

스키마 변경은 `supabase/migrations/`의 SQL 파일로 관리한다. 이런 변경 기록을 마이그레이션이라고 한다. 앱을 실행하는 일과 DB에 새 마이그레이션을 적용하는 일은 별개다. 절차는 [Supabase 마이그레이션 관리](../../engineering/database-migrations.md)를 따른다.

## 이어서 읽기

- [파일 저장소와 Supabase Storage](storage.md)
- [공통 인증·DB 기반](../../engineering/auth-foundation.md): 현재 인증 테이블과 함수

## 참고 자료

- [PostgreSQL: SQL 기초](https://www.postgresql.org/docs/current/tutorial-sql.html)
- [PostgreSQL: 트랜잭션](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [Supabase: 데이터베이스](https://supabase.com/docs/guides/database/overview)
- [Supabase: Data API](https://supabase.com/docs/guides/api)

[목차](../README.md)
