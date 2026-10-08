# 공개 문서 화면

`/docs/`에서 저장소의 Markdown 문서를 로그인 없이 읽을 수 있다. 기존 서비스와 메뉴·글꼴·화면 구성을 분리하며 인증 상태 조회 API를 호출하지 않는다. 문서 영역은 검색 결과 제외를 위해 `noindex, nofollow`를 제공한다.

## 원본과 공개 범위

원본은 저장소 루트 `docs/`에 유지한다. `docs/README.md`에서 연결된 Markdown과 해당 문서에서 연결한 Markdown을 재귀적으로 공개한다. 인덱스의 카테고리·제목·순서를 문서 메뉴에 사용한다. 새 문서를 메뉴에 표시하려면 인덱스에 링크를 추가한다.

인덱스에서 연결된 루트 `README.md`는 설치·실행 안내 보조 문서로 제공한다. 폴더 전체를 임의로 공개하지 않으며 `docs/superpowers/`, 숨김 파일·환경 파일·심볼릭 링크는 포함하지 않는다. 제외 경로나 누락된 Markdown 링크는 문서 생성 오류로 처리한다.

## 경로와 링크

| 원본 | 웹 경로 |
| --- | --- |
| `docs/README.md` | `/docs` |
| `docs/ARCHITECTURE.md` | `/docs/ARCHITECTURE` |
| `docs/engineering/login-auth.md` | `/docs/engineering/login-auth` |
| `docs/deployment/README.md` | `/docs/deployment` |
| `docs/local-development/setup/README.md` | `/docs/local-development/setup` |
| 루트 `README.md` | `/docs/project-readme` |

파일명 대소문자를 유지한다. 중첩 `README.md`는 해당 폴더 경로로 연결한다. 상대 Markdown 링크는 원본 파일 기준으로 해석해 문서 경로로 변환하며 쿼리·제목 앵커를 유지한다. 제목 ID와 목차는 GitHub 방식의 slug를 사용하며 같은 제목이 반복되면 순번을 붙인다. 외부 링크는 원래 대상을 유지한다.

본문의 코드·SQL·워크플로 상대 링크는 GitHub 저장소의 `main` 소스 파일로 연결한다. `backend/`, `frontend/`, `supabase/`, `scripts/`, `.github/` 경로를 허용하며 숨김 파일과 로컬 설계 경로는 제외한다. 이 파일의 내용은 문서 사이트에서 읽거나 제공하지 않는다.

## 화면

PC에서는 문서 메뉴·본문·본문 목차를 나란히 표시한다. 문서 메뉴는 카테고리별로 접고 펼칠 수 있으며 현재 문서가 속한 카테고리는 자동으로 펼친다. 모바일에서는 메뉴와 목차 전체를 접어 본문을 먼저 읽을 수 있다. 문서 헤더에서 문서 홈과 서비스 가이드로 이동한다.

제목·목록·표·코드·인용·GFM 체크 목록과 Mermaid 도표를 지원한다. 긴 표와 코드는 영역 안에서 가로 스크롤한다. Mermaid 도표 원본은 접을 수 있는 코드 영역에 제공하며 도표 렌더링 실패 시 코드를 펼쳐 표시한다. HTML·MDX 실행은 제공하지 않는다.

## 생성과 실행

`frontend/scripts/generate-docs.mjs`가 원본을 읽고 Git에서 제외한 `frontend/src/generated/docs.json`을 만든다. 루트 공통 실행기와 frontend의 `dev`·`build` 명령이 서버 시작·재시작과 프로덕션 빌드 전에 자동 생성한다. 생성 오류가 있으면 서버 시작 또는 빌드를 중단한다.

실행 중 문서를 변경하면 저장소 루트에서 다음 명령으로 갱신한다.

```sh
npm --prefix frontend run docs:generate
```

새 문서 경로를 추가했다면 개발 서버를 재시작한다. 배포 문서 변경은 다음 프론트엔드 빌드·배포에 반영된다. 빌드 결과의 문서 페이지는 정적으로 생성되며 런타임 파일 시스템과 백엔드에 의존하지 않는다. 존재하지 않는 문서 URL은 404를 반환한다.

## 레이아웃과 배포

`frontend/src/app/(service)/layout.tsx`가 서비스용 Provider·Toast·스타일을 관리한다. 루트 레이아웃은 공통 HTML과 메타데이터만 제공한다. `frontend/src/app/docs/`는 독립된 문서 레이아웃을 사용한다. 기존 서비스 URL은 유지되며 문서에서 서비스로 이동하면 서비스 인증 상태를 확인한다.

Vercel의 Root Directory는 `frontend`를 사용하고 외부 파일 포함 옵션을 활성화한다. `frontend/vercel.json`의 `ignoreCommand`가 프론트엔드·루트 docs·루트 README 변경을 빌드 대상으로 포함한다. 자세한 설정은 [Vercel 배포 안내](../deployment/vercel.md#공개-문서-빌드)를 따른다.

## 검증

```sh
npm test
npm --prefix frontend test
npm --prefix frontend run docs:generate
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

브라우저에서는 비로그인 문서 접근·상세 링크·새로고침·404, 인증 API 호출 부재, robots 메타데이터, PC·모바일 메뉴와 목차, 코드·표·Mermaid 스크롤, 문서와 서비스 사이의 이동을 확인한다.

[문서 목록](../README.md)
