# 프로젝트 문서

## 시스템을 이해할 때

- [시스템 아키텍처](ARCHITECTURE.md): 기술 스택, 폴더 구조, 구성 요소와 통신 방식
- [공통 API 응답 모델](engineering/api-response.md): 성공·오류 규격, 양쪽 모델과 호출·검증 방법
- [공용 화면과 배경 매핑](frontend/shared-ui.md): 메뉴 경로, 노출 기준, Figma 자산과 반응형 표시
- [인증 화면 디자인](frontend/auth-ui.md): 로그인·회원가입 화면, 입력 동작과 인증 API 연동 범위

## 처음 설치할 때

- [공통 설치 흐름](local-development/setup/README.md): 설치 대상 선택과 재설치
- [Windows 준비 사항](local-development/setup/windows.md)
- [macOS / Linux 준비 사항](local-development/setup/macos-linux.md)

## 로컬에서 개발할 때

- [실행·재시작·종료](local-development/runtime.md): 공통 실행기 사용
- [환경변수와 로컬 서비스](local-development/environment.md): 설정 기준과 서비스 주소
- [서버 개별 실행](local-development/manual-run.md): 공통 실행기 없이 직접 실행
- [로컬 개발환경 설치·실행 문제 해결](local-development/setup-runtime-troubleshooting.md)

## 코드를 변경하고 협업할 때

- [코딩과 검증 규칙](engineering/coding-conventions.md)
- [SMTP·Resend 이메일 발송](engineering/email-delivery.md): 모듈 설정·호출과 발송 오류 처리
- [커밋 메시지 작성 규칙](engineering/commit-messages.md): 타입별 기준과 작성 예시
- [PR 작성 규칙](engineering/pull-requests.md): Jira 작업 번호와 변경 내용·기능 테스트 범위
- [Jira 이슈 유형과 작업 분해 기준](engineering/jira-issue-guide.md)

## 배포할 때

- [Vercel / Render / Supabase Cloud 배포](deployment/README.md): 서비스별 설정, 메일 발신 도메인과 배포 후 확인

[프로젝트 README](../README.md)
