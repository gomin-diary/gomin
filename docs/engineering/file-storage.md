# Supabase Storage 파일 저장 모듈

파일 저장소는 **Supabase Storage**를 사용한다. 백엔드 공통 모듈이 기존 비동기 Supabase Python SDK 클라이언트로 파일 바이트를 저장한다.

## 사용하는 모듈

| 모듈 | 역할 |
| --- | --- |
| [backend/app/storage/supabase.py](../../backend/app/storage/supabase.py)의 `SupabaseFileStorage` | 파일 바이트를 Supabase Storage에 저장하고 `StoredFile` 반환 |
| [backend/app/storage/dependencies.py](../../backend/app/storage/dependencies.py)의 `get_file_storage` | FastAPI 의존성으로 공유 Supabase 클라이언트와 설정 주입 |
| [backend/app/core/config.py](../../backend/app/core/config.py)의 `Settings` | 대상 버킷과 파일 크기 제한 설정 |

공유 클라이언트는 기존 앱 수명 주기로 관리하며 저장 모듈이 별도로 생성하거나 종료하지 않는다.

## 호출 방법

```python
from app.storage.supabase import SupabaseFileStorage

storage = SupabaseFileStorage(supabase_client, settings)
stored = await storage.upload(file_bytes, content_type="application/pdf")
# stored.bucket: 저장 대상 버킷 ID
# stored.path: 모듈이 생성한 UUID 객체 경로
```

FastAPI의 호출 기능에서는 `Depends(get_file_storage)`로 모듈을 주입받을 수 있다. 사용자 권한 확인과 반환 경로의 업무 데이터 연결은 호출 기능에서 처리한다.

`upload(data: bytes, *, content_type: str = "application/octet-stream") -> StoredFile`은 다음과 같이 동작한다.

- 비어 있지 않은 `bytes`와 매개변수 없는 MIME type/subtype을 받는다. MIME은 소문자로 정규화한다.
- 실제 바이트 길이를 `STORAGE_MAX_FILE_SIZE_BYTES`와 비교한다.
- 요청마다 UUID 경로를 생성하고 `upsert=false`로 저장한다.
- Supabase의 성공 응답과 저장 경로를 확인한 뒤 버킷·경로만 반환한다.

원본 파일 이름을 저장 경로로 사용하지 않으며, 파일의 확장자보다 전달한 `content_type`으로 MIME을 지정한다. MIME 진위와 파일 내용은 호출 기능에서 검증한다.

## 설정

`backend/.env.example`을 기준으로 백엔드에서 설정한다.

| 설정 | 기본값 | 의미 |
| --- | --- | --- |
| `STORAGE_BUCKET` | `gomin-files` | Supabase에 미리 준비된 버킷 ID |
| `STORAGE_MAX_FILE_SIZE_BYTES` | `10485760` | 모듈이 허용하는 실제 파일 바이트 수, 기본 10MiB |
| `SUPABASE_URL` | 기존 설정 | Supabase 주소 |
| `SUPABASE_SECRET_KEY` | 기존 설정 | 백엔드 전용 서버 키 |

대상 버킷이 존재해야 하며 Supabase의 기존 버킷 제한도 업로드에 적용된다. 서버 키는 백엔드에서만 사용한다.

## 오류 처리

빈 파일·잘못된 타입·크기 초과·잘못된 MIME은 저장 요청 전에 `ValueError`로 거절한다. 제공자 오류·통신 실패·잘못된 응답은 `StorageUploadError`로 전달하며 제공자 오류 원문이나 키를 노출하지 않는다.

자동 재시도는 하지 않는다. 파일 전송 후 통신이 끊기면 실제 저장 결과가 불확실할 수 있으므로 호출 기능에서 재시도와 결과 확인을 결정한다.

## 검증

의존성이 설치된 Python으로 저장소 루트에서 실행한다. 테스트는 실제 환경 파일이나 서버 키를 읽지 않는다.

```sh
PYTHONPATH=backend python -m unittest discover -s backend/tests
```

실제 SDK와 HTTPX MockTransport로 파일 바이트·MIME·버킷·UUID 경로·덮어쓰기 금지·크기 검사·안전한 오류를 확인한다. 실제 Supabase Storage 저장은 대상 환경에서 별도 통합 확인이 필요하다.

[Supabase Python 파일 업로드](https://supabase.com/docs/reference/python/storage-from-upload) · [Storage 운영 설정](../deployment/supabase-storage.md) · [문서 목록](../README.md)
