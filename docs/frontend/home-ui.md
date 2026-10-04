# 홈 화면

로그인한 사용자가 `/`에서 고민일기 소개를 보고 **털어놓기**로 `/talk`에 이동한다.
기존 `AuthGuard`를 사용하며 비로그인 접근과 인증 조회 오류 처리는
[이메일 로그인과 세션](../engineering/login-auth.md#비로그인-접근-정책)을 따른다.

## 화면 구성

- PC: 사진 배경 왼쪽의 제목·소개·털어놓기 버튼과 오른쪽의 기울어진 메모.
- 모바일: 제목·소개 아래의 가이드·컬렉션·프로필 바로가기, 털어놓기 버튼과 메모.
- 제목은 “오늘, 어떤 이야기를 들려줄래?”, 소개는 “너의 고민이 모여 더 특별한 하루가 돼요.”다.
- 모바일 홈은 하단 네비게이션 바를 숨기고 본문의 가이드(`/guide`)·컬렉션(`/collection`)·프로필(`/settings`)만 표시한다. 다른 페이지의 하단 네비게이션은 유지한다. 가이드·컬렉션은 공용 경로 정의와 Figma 원본 아이콘을 사용한다. 프로필은 공용 Figma 원본 캐릭터를 재사용한다. 세 아이콘은 같은 96×72 표시 영역 안에서 원본 비율을 유지하며, 버튼 배경 없이 윤곽 그림자로 사진 위에서 식별한다.
- `PageShell`의 배경·공용 메뉴를 재사용한다. 홈 제목·소개는 Figma의 Gaegu, 본문 버튼·메뉴는 Noto Sans KR을 사용하며 상단 네비게이션은 공용 스타일을 유지한다. 홈 본문 스타일은 `frontend/src/app/home.module.css`에 둔다.

PC 소개·버튼의 왼쪽 여백은 화면 너비의 17.5%다. 제목과 버튼은 화면 너비에 맞춰 크기를 조절하고, 낮은 화면에는 위쪽 여백을 줄인다.
홈 본문은 화면 높이에 맞추며 스크롤하지 않는다. 모바일 제목·소개 크기와 여백은
공용 헤더를 제외한 본문 높이에 맞춰 조절한다. 일러스트 메뉴 아래에
원본처럼 중앙의 넓은 버튼과 별도의 우측 메모를 표시하며, 낮은 모바일 가로 화면에서는 소개와 메뉴를 좌우로 배치한다.

모든 이동은 실제 링크다. 제목과 본문 바로가기에 접근성 이름을 제공한다. PC 공용 메뉴는 현재 홈을 표시한다.
흰색 포커스 테두리로 사진 위에서도 키보드 초점을 구분한다.

## Figma 자산

Figma desktop Plugin API로 레이어 치수와 원문을 확인하고 원본 컴포넌트를 내보냈다.

- [PC 홈](https://www.figma.com/design/t66NuRwO9mgwGbLTc2allQ?node-id=39-49): 2560×1440.
- [모바일 홈](https://www.figma.com/design/t66NuRwO9mgwGbLTc2allQ?node-id=31-146): 1440×3120.

| 배포 파일 | 원본 노드 | 내보내기 규격 |
| --- | --- | --- |
| `frontend/public/images/home/home.svg` | `31:102` | 96×72 SVG |
| `frontend/public/images/home/guide.png` | `31:119` | 4× PNG, 384×288 |
| `frontend/public/images/home/collection.png` | `31:140` | 4× PNG, 384×288 |
| `frontend/public/images/home/arrow.svg` | `31:183` | 24×24 SVG |
| `frontend/public/images/home/memo.png` | `31:189` | 2× PNG, 그림자를 포함한 388×300 |

가이드·컬렉션은 Figma 원본의 형태·채움·색상을 보존한 투명 PNG를 사용한다. 프로필은 `frontend/public/images/navigation/profile-character.png`의 Figma 원본 캐릭터를 사용하며, 표시 영역 높이에 맞춘다. 표시할 때 원본 비율을 유지한다.
메모는 투명한 그림자를 포함한 원본 이미지와 대체 문구를 사용한다.
사진 배경과 공용 네비게이션 출처는 [공용 화면과 배경 매핑](shared-ui.md)을 따른다.
런타임에는 `frontend/public` 자산만 사용한다.

## 서체와 배경 초점

[Google Fonts의 Gaegu](https://github.com/google/fonts/tree/main/ofl/gaegu)와
[Noto Sans KR](https://github.com/google/fonts/tree/main/ofl/notosanskr)의 공식 파일을
홈에 사용하는 글자만 포함한 WOFF2로 제공한다. 해당 OFL 라이선스를 `frontend/public/fonts`에 함께 보관한다.
공용 화면의 기존 서체는 유지하고 홈에만 적용한다.

홈 배경은 캐릭터 얼굴의 가로 위치를 중심에 맞춘다. PC는 원본의 가로 60.5%·세로 74%,
모바일은 가로 51%·세로 73%를 초점으로 잡아 원본 비율을 유지하며 화면 바깥 부분을 자른다.
모바일 배경은 화면 전체에 표시하며, 낮은 가로 화면에도 캐릭터가 보이도록 크기를 확보한다.

## 검증

[코딩과 검증 규칙](../engineering/coding-conventions.md)의 lint·typecheck를 수행한다.
브라우저에서는 PC·모바일·작은 화면·가로 화면에서 다음을 확인한다.

- 제목·소개·메모·자산의 로딩과 비율, 가로·세로 넘침 없이 한 화면에 모든 요소가 표시되는지.
- 털어놓기의 대화 이동, 일러스트 바로가기와 공용 메뉴의 경로·현재 메뉴 표시.
- 키보드 탐색과 본문 건너뛰기, 버튼과 메모가 화면 안에 표시되는지.
- 인증 응답에 따른 홈 표시·비로그인 이동·조회 오류에서 본문 숨김.

실제 모바일 기기의 안전영역, Safari와 배포 환경은 별도 검증한다.
대화 처리·그림 생성·컬렉션 저장 기능은 홈 화면의 범위에 포함하지 않는다.

[문서 목록](../README.md)
