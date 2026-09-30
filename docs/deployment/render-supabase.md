# Render + Supabase Cloud 배포

Render의 Environment에 다음 값을 등록합니다. 프로젝트 URL과 Secret 키는 해당 Supabase Cloud 프로젝트의 Connect/API Keys 화면에서 확인합니다.

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY=<Supabase Cloud의 Secret 키>
CORS_ORIGINS=["https://<프론트엔드 도메인>"]
```

DB 비밀번호나 `DATABASE_URL`은 백엔드 실행에 필요하지 않습니다. Secret 키는 서버 전용이며 프론트엔드 환경 변수에 넣지 않습니다. 이 키는 Supabase 계정용 Personal Access Token과 다릅니다.

Render의 Root Directory는 `backend`, Build Command는 `pip install -r requirements.txt`, Start Command는 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`로 지정합니다. Python 3.12 이상을 사용합니다. `backend/.python-version`의 `3.12`는 배포 기본 버전이며 최소 버전 제한과는 별개입니다. 다른 버전으로 배포하려면 해당 파일도 맞춰 변경하세요.

Supabase Cloud에서 Data API를 활성화하고 `public` 스키마를 노출해야 합니다. 배포 전 `supabase/migrations/`의 SQL을 해당 프로젝트에 적용합니다. 현재 상태 확인 함수는 Supabase SQL Editor에서 `20260929000000_health_check.sql` 내용을 실행하면 추가할 수 있습니다. 애플리케이션은 시작할 때 스키마를 변경하지 않습니다.

[문서 목록](../README.md)
