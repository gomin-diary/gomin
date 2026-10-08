# 프로젝트 문서

## 시작하기·로컬 개발

- [공통 설치 흐름](local-development/setup/README.md): 설치 대상 선택과 재설치
- [Windows 준비 사항](local-development/setup/windows.md)
- [macOS / Linux 준비 사항](local-development/setup/macos-linux.md)
- [실행·재시작·종료](local-development/runtime.md): 공통 실행기 사용
- [환경변수와 로컬 서비스](local-development/environment.md): 설정 기준과 서비스 주소
- [서버 개별 실행](local-development/manual-run.md): 공통 실행기 없이 직접 실행
- [로컬 개발환경 설치·실행 문제 해결](local-development/setup-runtime-troubleshooting.md)
- [로컬 테스트 사용자](local-development/test-users.md): 회원가입과 함께 제공하는 더미 계정 3개와 seed 적용

## 시스템·공통 모듈

- [시스템 아키텍처](ARCHITECTURE.md): 기술 스택, 폴더 구조, 구성 요소와 통신 방식
- [공통 API 응답 모델](engineering/api-response.md): 성공·오류 규격, 양쪽 모델과 호출·검증 방법
- [SMTP·Resend 이메일 발송](engineering/email-delivery.md): 모듈 설정·호출과 발송 오류 처리
- [Supabase Storage 파일 저장 모듈](engineering/file-storage.md): Supabase 저장 모듈·의존성 주입·설정과 사용 방법

## 인증

- [공통 인증·DB 기반](engineering/auth-foundation.md): 인증 4개 테이블·DB 함수, 암호화·세션·쿠키와 직접 API 호출
- [회원가입 구현](engineering/signup.md): 이메일 인증·일회용 증표·약관·세션 API와 검증 범위
- [이메일 로그인과 세션](engineering/login-auth.md): 로그인 API·세션 쿠키·화면 연동과 검증
- [Google OAuth 흐름 관리](engineering/google-oauth-flow.md): 인증 호출 순서·상태 수명·화면 복귀·예외 처리의 관리 기준
- [인증 화면 디자인](frontend/auth-ui.md): 로그인·회원가입 화면, 입력 동작과 인증 API 연동 범위

## 화면·사용자 흐름

- [공용 화면과 배경 매핑](frontend/shared-ui.md): 메뉴 경로, 노출 기준, Figma 자산과 반응형 표시
- [홈 화면](frontend/home-ui.md): 소개·대화 시작, PC·모바일 배치와 Figma 자산 출처
- [가이드 화면](frontend/guide-ui.md): 이용 단계, PC·모바일 배치와 Figma 일러스트 출처
- [컬렉션 조회 화면](frontend/collection-ui.md): 모든 로그인 회원의 공통 더미 목록·상세, PC 필름·팝업, 모바일 상세와 검증
- [공개 문서 화면](frontend/docs-ui.md): `/docs/` 공개 범위, 문서 생성·링크·레이아웃과 배포
- [공개 문서 영역 설계 — 검토안](https://younkim.atlassian.net/wiki/spaces/GOMIN/pages/3670018): 원본 Markdown을 유지하는 `/docs/` 공개 화면 설계

## 데이터베이스

- [대화·컬렉션 ERD](engineering/conversation-collection-erd.md): 테이블·관계·제약조건, Supabase SQL과 ID 생성·재시도 관련 질문·답변
- [Supabase 마이그레이션 관리](engineering/database-migrations.md): SQL 작성·검토, 로컬·PR 검증, 운영 적용과 실패 처리

## 개발·협업

- [코딩과 검증 규칙](engineering/coding-conventions.md)
- [커밋 메시지 작성 규칙](engineering/commit-messages.md): 타입별 기준과 작성 예시
- [PR 작성 규칙](engineering/pull-requests.md): 프로젝트 스킬, Jira 작업 번호·변경 내용·개조체 작성 기준
- [이슈 유형과 작업 분해 기준](engineering/jira-issue-guide.md)
- [설계문서 보관 규칙](engineering/design-document-storage.md): 로컬 제외 경로, 공유 설계문서 등록과 관련 작업 연결

## 배포·운영

- [배포·운영 개요](deployment/README.md): 서비스 구성, 공통 배포 순서와 배포 후 확인
- [Vercel — Next.js](deployment/vercel.md): 프론트엔드 빌드·환경변수·공개 문서와 배포 확인
- [Render — FastAPI·Uvicorn](deployment/render.md): 백엔드 실행·인증·Google OAuth·메일 설정과 배포 확인
- [Supabase — 데이터베이스](deployment/supabase-database.md): Data API·서버 연결·운영 마이그레이션과 DB 상태 확인
- [Supabase — Storage](deployment/supabase-storage.md): 업로드 모듈·버킷·크기·MIME 제한과 운영 확인 범위
- [UptimeRobot — 모니터링](deployment/uptimerobot.md): 백엔드 상태 API의 5분 간격 확인·이메일 알림과 장애 대응

[프로젝트 README](../README.md)
