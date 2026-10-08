# 배포·운영

Vercel의 Next.js, Render의 FastAPI·Uvicorn, Supabase Cloud의 DB·Storage와 UptimeRobot을 운영한다. 이 문서는 서비스별 안내와 공통 배포 순서를 연결한다. 자동 배포 트리거·대상 브랜치·도메인의 실제 설정은 각 서비스의 프로젝트 대시보드에서 확인한다.

## 서비스별 안내

| 서비스 | 역할 | 상세 문서 |
| --- | --- | --- |
| Vercel | Next.js 화면과 공개 문서 빌드·배포 | [프론트엔드 운영](vercel.md) |
| Render | FastAPI·Uvicorn 실행, 인증·메일 설정 | [백엔드 운영](render.md) |
| Supabase DB | PostgreSQL·Data API와 운영 마이그레이션 | [데이터베이스 운영](supabase-database.md) |
| Supabase Storage | 파일 저장 버킷과 업로드 제한 | [Storage 운영](supabase-storage.md) |
| UptimeRobot | 백엔드 상태 API의 주기적 확인·이메일 알림 | [모니터링 운영](uptimerobot.md) |

## 공통 배포 순서

1. 변경 범위에 맞는 [코드·문서 검증](../engineering/coding-conventions.md)을 수행하고 PR을 검토한다.
2. DB 변경이 있으면 `main`에서 운영 마이그레이션을 실행하고 스키마·권한·적용 이력을 확인한다. 자세한 절차는 [Supabase 마이그레이션 관리](../engineering/database-migrations.md)를 따른다.
3. Storage를 사용하는 기능은 [버킷과 제한 설정](supabase-storage.md#운영-버킷-준비)을 확인한다. 공통 저장 모듈이 버킷을 자동 생성하지 않는다.
4. Render의 런타임·인증·메일 설정을 확인하고 백엔드를 배포한다. DB 변경이 필요한 릴리스에서는 DB 적용과 백엔드 자동 배포의 실행 순서를 맞춘다.
5. Vercel의 API 주소·공유 이미지 출처와 빌드 설정을 확인하고 프론트엔드를 배포한다. 프론트엔드 환경변수를 바꾸면 다시 빌드한다.
6. 아래 배포 후 확인을 수행하고 UptimeRobot의 대상 주소·5분 주기·이메일 알림 설정을 확인한다.

DB 마이그레이션, 앱 배포, Storage 준비, 모니터 설정은 각각 별도 작업이다. 한 서비스의 배포 성공만으로 나머지 작업이 완료됐다고 판단하지 않는다.

## 배포 후 확인

| 대상 | 확인 내용 |
| --- | --- |
| 프론트엔드 | 페이지·정적 파일·공유 이미지와 비로그인 공개 문서 접근 |
| 백엔드 | `/api/v1/health`의 HTTP 200과 `data.status: "ok"` |
| DB | `/api/v1/health/db`의 HTTP 200과 `data.database: "connected"`, 변경한 업무 데이터 동작 |
| 인증 | 실제 프론트엔드 Origin의 CORS 허용, HTTPS 세션 쿠키, 로그인·로그아웃 |
| 메일 | 인증 메일의 제공자 접수 결과와 실제 수신 |
| Storage | 해당 기능의 업로드 결과·객체 경로와 접근 모델에 맞는 파일 읽기 |
| 모니터링 | UptimeRobot의 대상·주기·이메일 알림 연락처와 모니터 상태 |

현재 UptimeRobot은 `/api/v1/health`를 5분마다 확인한다. DB·Storage·메일·화면의 기능 검증 범위와 구분하며 상세 대응은 [모니터링 문서](uptimerobot.md)를 따른다.

[문서 목록](../README.md)
