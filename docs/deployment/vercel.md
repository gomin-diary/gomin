# Vercel — Next.js

`frontend/`의 Next.js 애플리케이션을 배포한다. 운영 배포 브랜치·자동 배포 트리거·도메인은 해당 Vercel 프로젝트 설정에서 확인한다.

## 빌드 설정

| 항목 | 설정 |
| --- | --- |
| Framework Preset | Next.js |
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| 루트 외부 파일 | 저장소 루트의 `docs/`와 `README.md`를 빌드에서 읽을 수 있도록 포함 |

`frontend/package.json`의 `prebuild`가 문서를 생성한 뒤 Next.js를 빌드한다. 루트 외부 파일 포함 설정도 함께 확인한다. [Vercel 빌드 설정](https://vercel.com/docs/builds/configure-a-build)

## 환경변수와 공유 이미지

Frontend는 `frontend/`의 Next.js 애플리케이션입니다. `frontend/package.json`에 `build`, `start`, `lint`, `typecheck` 명령이 정의되어 있습니다. 공통 API 함수는 `NEXT_PUBLIC_API_BASE_URL`을 사용하며, 배포 시 Render API 주소를 설정합니다. `frontend/.env.example`의 루프백 주소는 로컬 개발용입니다. 서버 Secret 키를 `NEXT_PUBLIC_` 변수에 넣지 않습니다.

공유 이미지의 절대 URL은 `NEXT_PUBLIC_SITE_URL`을 기준으로 생성한다. 커스텀 도메인을 사용하면 이 값을 실제 공개 출처(예: `https://your-domain.com`)로 설정하고 재빌드한다. 값이 없으면 Vercel의 `VERCEL_PROJECT_PRODUCTION_URL`, `VERCEL_URL` 순서로 사용하며 로컬에서는 `http://localhost:3000`으로 폴백한다. 배포 후 페이지의 `og:image`가 공개 HTTPS 주소인지와 이미지 접근이 가능한지 확인한다.

## 공개 문서 빌드

Root Directory는 `frontend`를 사용하며 **Include files outside the root directory in the Build Step**을 활성화한다. 빌드 전 문서 생성 스크립트가 루트 `docs/`와 `README.md`를 읽는다.

`frontend/vercel.json`의 `ignoreCommand`는 다음 명령을 사용한다. 파일 설정이 대시보드의 Ignored Build Step을 대체한다. [Vercel 설정 문서](https://vercel.com/docs/project-configuration/vercel-json#ignorecommand)

```sh
git diff HEAD^ HEAD --quiet -- . ../docs ../README.md
```

프론트엔드·문서·루트 README 변경 시 빌드하며 그 외 변경만 있으면 생략한다. 문서 생성·공개 범위와 갱신 방법은 [공개 문서 화면](../frontend/docs-ui.md)을 따른다. 배포 후 `/docs/`와 상세 문서를 비로그인 상태에서 열고 문서 변경 반영과 검색 제외 메타데이터를 확인한다.

## 배포 후 확인

- 페이지·정적 파일·공유 이미지가 실제 공개 HTTPS 주소에서 열리는지 확인한다.
- `/docs/`와 상세 문서를 비로그인 상태에서 열고 문서 변경 반영·링크 이동·검색 제외 메타데이터를 확인한다.
- 배포된 화면에서 Render API로 요청이 전달되는지 확인한다. 홈 화면 표시만으로 API·DB 정상 동작을 판단하지 않는다.
- 로그인·회원가입과 보호 화면 이동에서 쿠키와 CORS 동작을 확인한다. [인증·백엔드 설정](render.md#회원가입-인증-설정)을 함께 따른다.

[배포·운영 개요](README.md) · [문서 목록](../README.md)
