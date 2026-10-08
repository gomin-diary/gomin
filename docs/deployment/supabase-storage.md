# Supabase — Storage

백엔드의 공통 저장 모듈이 기존 Supabase 버킷에 파일 바이트를 업로드한다. 모듈의 호출 방법과 오류 계약은 [파일 저장 모듈](../engineering/file-storage.md)을 따른다. 이 문서는 운영에 필요한 버킷·제한 설정과 확인 범위를 설명한다.

## 코드로 확인되는 설정

[백엔드 설정](../../backend/app/core/config.py)과 [저장 모듈](../../backend/app/storage/supabase.py)의 기준은 다음과 같다. 기본값은 운영 대시보드의 실제 설정을 의미하지 않는다.

| 항목 | 현재 코드 기준 |
| --- | --- |
| 버킷 ID | `STORAGE_BUCKET`, 기본값 `gomin-files` |
| 애플리케이션 크기 제한 | `STORAGE_MAX_FILE_SIZE_BYTES`, 기본값 `10485760`바이트(10MiB) |
| 업로드 경로 | 요청마다 생성한 UUID, `upsert=false` |
| MIME 검사 | 매개변수 없는 MIME type/subtype 형식 검사. 특정 MIME 허용 목록은 없음 |
| 버킷 생성 | 앱과 저장소 마이그레이션에서 생성하지 않음 |
| 버킷 공개 여부·접근 정책 | 저장소에서 public/private 설정과 Storage 정책을 정의하지 않음 |

현재 `main`에는 공통 업로드 모듈과 FastAPI 의존성이 있으며, 이를 호출하는 파일 업로드 API와 서명 URL 발급 API는 연결되어 있지 않다. 모듈이 있다는 사실만으로 서비스 화면에서 업로드·다운로드가 가능하다고 판단하지 않는다.

`supabase/config.toml`의 `[storage] file_size_limit = "50MiB"`는 **로컬 Supabase 설정**이다. 운영 프로젝트의 전역 제한과 버킷별 제한은 별도로 확인한다. 코드만으로 운영 버킷의 존재·공개 여부·MIME 제한을 확정할 수 없다.

## 운영 버킷 준비

1. 대상 Supabase Cloud 프로젝트에 사용할 버킷이 존재하는지 확인한다. Render의 `STORAGE_BUCKET`과 실제 버킷 ID를 맞춘다.
2. 버킷의 public/private 설정과 접근 정책을 확인한다. 공개 버킷은 파일 URL로 읽을 수 있고, 비공개 버킷은 권한 있는 다운로드나 유효한 서명 URL이 필요하다. 현재 공통 모듈은 업로드 후 버킷·경로만 반환한다. [Supabase 버킷 접근 모델](https://supabase.com/docs/guides/storage/buckets/fundamentals)
3. 운영 프로젝트의 전역 크기 제한과 버킷별 크기·MIME 제한을 확인하고 애플리케이션 제한과 맞춘다. Supabase 측 제한도 업로드에 적용된다. [버킷별 업로드 제한](https://supabase.com/docs/guides/storage/buckets/creating-buckets#restricting-uploads)
4. 버킷·정책을 새로 정의하거나 변경할 때는 [마이그레이션 관리](../engineering/database-migrations.md)의 변경·검토·운영 적용 절차를 따른다. 운영 대시보드 변경만으로 저장소의 관리 기준을 대체하지 않는다.

## 백엔드 설정

설정 이름은 `backend/.env.example`을 따른다. Render에 기존 `SUPABASE_URL`, `SUPABASE_SECRET_KEY`와 함께 `STORAGE_BUCKET`, `STORAGE_MAX_FILE_SIZE_BYTES`를 등록하고 변경 후 백엔드를 재배포한다. 서버 전용 키는 브라우저에 전달하지 않는다.

## 운영 확인과 오류 대응

저장 모듈을 사용하는 통합 확인에서 통제된 테스트 파일을 업로드하고 반환한 버킷·경로의 객체가 생성됐는지 확인한다. 읽기 검증은 해당 버킷의 접근 모델과 실제 제공하는 다운로드 방식에 맞춰 수행한다. `/api/v1/health/db` 성공은 Storage의 정상 동작을 보장하지 않는다.

| 증상 | 확인할 내용 |
| --- | --- |
| 저장 요청 전 크기·MIME 검사 실패 | 실제 바이트 수, 애플리케이션 제한, 전달한 MIME 형식 |
| Storage 업로드 실패 | 버킷 존재, 서버 키 권한, 전역·버킷별 제한, 제공자 연결 상태 |
| 저장 후 파일을 읽지 못함 | public/private 설정과 다운로드 권한·서명 URL 제공 여부 |
| 통신 중단 후 저장 결과 불명확 | 객체 생성 여부를 확인하고 재시도 결정. 모듈은 자동 재시도하지 않음 |

모듈은 제공자 오류를 `StorageUploadError`로 전달한다. 운영 확인에서 오류 원문이나 서버 키를 공개하지 않는다.

[DB 운영](supabase-database.md) · [배포·운영 개요](README.md) · [문서 목록](../README.md)
