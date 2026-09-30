# 폴더 구성

```text
frontend/                       Next.js · TypeScript · App Router · Zustand
  src/app/                      페이지와 루트 레이아웃
  src/components/               UI 컴포넌트
  src/providers/                앱 전역 Zustand Provider
  src/stores/                   클라이언트 UI 상태
  src/lib/api.ts                백엔드 요청 함수
backend/                        FastAPI · Uvicorn · Supabase Python SDK
  app/config.py                 환경변수
  app/database.py               Supabase 클라이언트와 의존성
  app/main.py                   앱 수명주기와 기본 API
supabase/                       로컬 Supabase 설정과 DB 마이그레이션
scripts/
  setup.cmd                     모든 OS에서 사용하는 설치 진입 파일
  setup.sh                      macOS/Linux의 nvm·Node·의존성 설치
  setup.ps1                     Windows의 환경 확인·의존성 설치
  setup-node.ps1                Windows nvm·Node 설치 및 버전 전환
  dev.mjs                       공통 개발 서버 실행·재시작·종료
  tests/                        설치·실행기 회귀 테스트
  dev.sh, dev.ps1, restart.sh    기존 명령의 호환 진입 파일
  export-mobile-backgrounds.py  모바일 배경 이미지 내보내기
assets/, public/, figma/         디자인 자료와 이미지 리소스
docs/
  setup/                        OS별 설치 안내
  development/                  구조·실행·환경변수·개발 규칙·문제 해결
  deployment/                   배포 안내
.dev/                           실행기 잠금 파일과 로컬 제어 연결 정보 (Git 제외)
```

환경 파일과 의존성 디렉터리는 각 앱 아래에 생성됩니다. `frontend/.env.local`, `backend/.env`, `node_modules/`, `backend/.venv/`는 Git에 포함하지 않습니다. `package-lock.json`과 `backend/requirements.txt`는 설치 버전을 고정합니다.

[문서 목록](../README.md)
