# Supabase 데이터베이스 마이그레이션 관리

DB 스키마와 운영에 필요한 데이터 변경은 Supabase CLI와 `supabase/migrations/`의 SQL로 관리한다. 로컬과 운영은 같은 마이그레이션 파일을 사용한다. FastAPI가 시작할 때 운영 스키마를 변경하지 않는다.

## 변경 원칙

- 작업 브랜치에서 마이그레이션을 작성하고 PR로 검토한다. `main`에서 직접 변경하지 않는다.
- 테이블·제약·인덱스·함수·권한·RLS와 운영 데이터 변경을 SQL 파일로 남긴다. SQL Editor에서 직접 변경한 결과만으로 작업을 끝내지 않는다.
- 이미 공유하거나 적용한 파일은 수정·삭제·이름 변경하지 않는다. 수정 사항은 새로운 마이그레이션으로 추가한다.
- 파일명은 CLI가 생성한 `<timestamp>_<name>.sql`을 사용한다. 병합 전에 버전 중복과 순서를 확인하고 이전 파일에 대한 의존성을 검토한다.
- 서버가 Data API로 사용할 객체에는 필요한 `service_role` 권한과 RLS를 함께 정의한다. 광범위한 사용자 권한을 임의로 추가하지 않는다.
- 운영 배포 시 기존 앱이 계속 동작하도록 호환성을 유지한다. 컬럼 추가·데이터 이관·앱 전환·기존 컬럼 제거처럼 단계가 필요한 변경은 여러 릴리스로 나눈다.
- 비밀값·개인정보·실제 사용자 데이터는 SQL에 넣지 않는다. 로컬 테스트 데이터는 `supabase/seed.sql`에 두고 운영에 적용하지 않는다.

## 로컬 작성과 확인

저장소 루트에서 실행한다.

```sh
npm run db:migration:new -- 변경_이름
```

생성된 SQL을 작성한 뒤 로컬 Supabase가 실행 중인 상태에서 적용한다.

```sh
npm run db:migrate
```

공통 실행기의 `npm run dev`, `npm run dev:all`, `npm run dev:backend`도 백엔드 시작 전에 로컬 미적용 마이그레이션을 적용한다. 프론트엔드만 시작하면 DB 마이그레이션은 실행하지 않는다.

스키마와 권한, 관련 API의 정상·실패 동작을 확인한다. DB 상태 API는 연결과 상태 확인 함수의 호출만 검사하므로 업무 데이터 변경 검증을 대신하지 않는다. 전체 적용 순서는 개발 DB와 분리된 임시 DB에서 확인한다. `db reset`은 데이터를 초기화하므로 보존해야 할 개발 DB에 검사 목적으로 실행하지 않는다.

## PR 검증

[Supabase migration check](../../.github/workflows/supabase-migrations-check.yml)는 `main` 대상 PR에서 Supabase 파일·루트 의존성·마이그레이션 워크플로가 변경되면 실행한다. 수동 실행도 가능하다.

고정된 CLI를 설치한 뒤 임시 PostgreSQL을 시작하고, seed 없이 전체 마이그레이션을 적용하고 재실행한다. 운영 Secrets와 운영 DB에는 접근하지 않는다. 이 검사는 빈 DB의 적용 순서와 SQL 실행을 확인하며 기존 운영 데이터의 이관·성능·잠금 경합까지 검증하지는 않는다.

## 운영 설정과 적용

GitHub 저장소의 **Settings → Environments → supabase-production**에 세 값을 모두 Environment secrets로 등록한다. Deployment branches는 `main`만 허용하며 Vercel의 `Production` 환경과 별도로 관리한다.

| 이름 | 값 |
| --- | --- |
| `SUPABASE_ACCESS_TOKEN` | 대상 프로젝트에 접근하는 Supabase Personal Access Token |
| `SUPABASE_DB_PASSWORD` | 대상 프로젝트의 DB 비밀번호 |
| `SUPABASE_PROJECT_ID` | 대시보드 URL의 `/project/` 뒤 프로젝트 ref |

Personal Access Token은 백엔드의 `SUPABASE_SECRET_KEY`와 다르다. `supabase link`에 필요한 프로젝트 설정·API 키·API 키 비밀의 읽기 권한을 대상 프로젝트에 부여한다. 실제 값은 코드·문서·채팅·Jira에 기록하지 않는다. 공개 저장소의 PR 검증에는 운영 Secrets를 전달하지 않는다.

1. PR의 SQL과 검증 결과를 확인하고 `main`에 병합한다.
2. 기존 운영 스키마와 적용 이력의 일치 여부, 데이터 변경 영향, 복구 방법을 확인한다.
3. Actions의 [Supabase production migrations](../../.github/workflows/supabase-migrations-production.yml)에서 `Run workflow`를 선택하고 `main`으로 실행한다.
4. 성공한 뒤 관련 스키마·권한·API 동작을 확인하고 Render 백엔드를 배포한다.

운영 워크플로는 프로젝트 연결 후 `db push --dry-run`으로 미적용 목록을 표시하고 `db push`로 적용한다. `main` 외 브랜치는 실행하지 않는다. seed와 Vault 설정은 적용하지 않으며 설정 누락이나 적용 실패 시 중단한다. 운영 실행을 동시에 처리하지 않는다. Render 배포는 자동으로 제어하지 않으므로 DB 변경이 필요한 릴리스에서는 자동 배포 트리거와 실행 순서를 맞춘다.

## 적용 이력과 실패 처리

Supabase는 `supabase_migrations.schema_migrations`에서 적용 이력을 관리한다. 이미 기록된 버전은 재실행하지 않는다. 적용한 파일의 내용을 바꾸는 대신 새 버전으로 변경을 남긴다.

- 실패하면 앱 배포를 중단하고 어느 버전까지 적용됐는지와 현재 스키마를 먼저 확인한다. 전체 파일이 모두 롤백됐다고 가정하지 않는다.
- 기존 운영 스키마를 SQL Editor 등으로 변경했다면 실제 객체와 마이그레이션 이력을 대조해 최초 적용 기준을 맞춘다.
- `migration repair`는 적용 이력을 수정하며 SQL 변경을 실행하거나 되돌리는 명령이 아니다. 실제 적용 여부를 확인한 경우에만 사용한다.
- 이력 불일치를 숨기려고 `--include-all`, 적용 기록 삭제, 운영 `db reset`을 사용하지 않는다.
- 이미 적용된 변경을 되돌릴 때도 새로운 보정 마이그레이션을 작성한다. 삭제된 데이터 복구가 필요하면 사전에 준비한 백업·복구 절차를 사용한다.

[Supabase 마이그레이션](https://supabase.com/docs/guides/deployment/database-migrations) · [Supabase 환경 관리](https://supabase.com/docs/guides/deployment/managing-environments) · [배포 안내](../deployment/README.md) · [문서 목록](../README.md)
