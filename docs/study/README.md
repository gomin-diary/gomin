# 웹 개발 기초

## 목차

| 순서 | 주제 | 주요 내용 |
| --- | --- | --- |
| 1 | [웹 서비스는 어떻게 움직일까](web/web-basics.md) | 브라우저, 클라이언트·서버, 화면과 데이터 저장소의 역할 |
| 2 | [HTTP와 요청·응답](web/http.md) | URL, 요청·응답 메시지, 상태 코드, JSON, HTTPS |
| 3 | [API란 무엇일까](api/api-basics.md) | API와 HTTP API, 엔드포인트, 명세, SDK |
| 4 | [REST API](api/rest-api.md) | 리소스와 표현, HTTP 메서드, 멱등성, REST의 원칙 |
| 5 | [프론트엔드와 Next.js](application/frontend.md) | HTML·CSS·JavaScript, React, 컴포넌트, 렌더링 |
| 6 | [백엔드와 FastAPI·Uvicorn](application/backend.md) | 라우팅, 검증, 서버 프로그램, 비동기 처리 |
| 7 | [데이터베이스와 Supabase](data/database.md) | 테이블과 관계, 키, SQL, 트랜잭션, Data API |
| 8 | [파일 저장소와 Supabase Storage](data/storage.md) | 파일과 메타데이터, 버킷, 객체 경로, 접근 범위 |
| 9 | [인증과 인가](application/authentication.md) | 사용자 확인과 권한, 쿠키·세션·토큰 |
| 10 | [CORS와 출처](application/cors.md) | 동일 출처 정책, 사전 요청, 쿠키 전송 조건 |
| 11 | [배포의 기본 개념](deployment/deployment-basics.md) | 로컬·운영, 빌드·실행, 환경변수, 도메인 |
| 12 | [배포 플랫폼의 역할](deployment/platforms.md) | Vercel·Render·Supabase의 역할과 서비스 간 연결 |
| 13 | [모니터링과 UptimeRobot](operations/monitoring.md) | 로그·지표, 가용성, 상태 확인 API와 검사 범위 |

- [웹 개발 용어 사전](glossary.md)

## 프로젝트 참고 문서

| 필요할 때 | 참고 문서 |
| --- | --- |
| 실제 구성 요소와 코드 위치 확인 | [시스템 아키텍처](../ARCHITECTURE.md) |
| 로컬 설치·실행 | [공통 설치 흐름](../local-development/setup/README.md), [실행·재시작·종료](../local-development/runtime.md) |
| API 성공·실패 응답 형식 확인 | [공통 API 응답 모델](../engineering/api-response.md) |
| 인증 구현과 설정 확인 | [공통 인증·DB 기반](../engineering/auth-foundation.md) |
| 파일 저장 모듈 사용 | [Supabase Storage 파일 저장 모듈](../engineering/file-storage.md) |
| 운영 배포 설정 확인 | [배포 안내](../deployment/README.md) |
| DB 구조·권한 변경 | [Supabase 마이그레이션 관리](../engineering/database-migrations.md) |

[프로젝트 문서 목록](../README.md)
