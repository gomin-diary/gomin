# 컬렉션 조회 화면

[GOMIN-27](https://younkim.atlassian.net/browse/GOMIN-27)의 최신 범위와
[컬렉션 요구사항](https://younkim.atlassian.net/wiki/spaces/GOMIN/pages/557105)을 기준으로
GOMIN-28~36의 목록·상세 조회 화면을 더미 데이터로 구현한다.
저장·스키마·마이그레이션은 털어놓기 담당 GOMIN-74의 범위다.
기존 [분석 문서](https://younkim.atlassian.net/wiki/spaces/GOMIN/pages/3473409)의 DB/API 제안을
확정된 구현으로 취급하지 않는다.

## 화면과 탐색

- 경로는 `/collection`이며 공용 AuthGuard와 자체 세션을 재사용한다.
  비회원은 로그인 후 컬렉션으로 복귀한다.
- PC는 기존 책상 배경·메뉴 위에 연결된 필름을 표시한다. 한 번에 최대 6개를
  표시하며 6개 단위로 이동한다. 양 끝에서 순환하지 않는다.
- PC 상세는 이미지 없이 날짜·제목·위로 문구·지금의 마음·주요 고민·감정을
  중앙 팝업으로 표시한다. 닫기 버튼·Escape·바깥 영역·브라우저 뒤로가기로
  닫으며 목록 위치와 선택 버튼 포커스를 유지한다. 기본 dialog로 포커스를 제한한다.
- 모바일은 감정 필터와 2열 필름 목록을 제공한다. 필터는 Figma의
  전체·기쁨·슬픔·불안·관계·일상을 따른다.
- 모바일 상세는 dialog가 아닌 화면 전체를 덮는 article이다. 선택한 기록의
  이미지와 같은 요약을 표시하고 공용 메뉴는 숨긴다. 왼쪽 위 텍스트 없는
  뒤로가기 버튼과 브라우저 뒤로가기로 기존 목록 위치·필터에 복귀한다.
- 선택 기록은 `#entry=<기록 ID>`로 표시한다. 새로고침과 브라우저 앞·뒤 이동에도
  해당 ID를 공통 더미 저장소에서 다시 조회한다.
- 조회 0건·조회 실패·로딩은 서로 다른 상태다. 실패 시 재시도를 제공하며
  없는 기록의 상세는 ‘기록을 찾을 수 없어요’ 상태다.
- 빈 상태의 ‘오늘의 마음을 털어놓고, 첫 번째 이야기를 남겨보세요’와
  `/talk` 이동은 임시 UX다. 최종 문구·정렬·PC 이동량·필터 분류는 팀 합의로
  조정할 수 있다. 더미 목록은 Figma의 표시 순서를 사용한다.

Figma 상세의 ‘이 이야기 이어서 보기’ 버튼은 현재 준비 중 안내만 제공한다.
기존 `/talk`은 준비 화면이고 대화 재개 인터페이스가 없으므로 이전 대화를 재개하거나
새 대화를 임의로 시작하지 않는다. 검색·수정·삭제·즐겨찾기·공개 공유는 포함하지 않는다.

## 실제 API 조회

서비스 기본 화면은 `createApiCollectionRepository(apiFetch)`로 자체 세션의 컬렉션 API를 호출한다.
공통 fixtures와 모의 Repository는 테스트에만 사용하며 `collectionPreview` 쿼리는 서비스에 적용하지 않는다.
entry ID로 상세를 조회하고 diary_date·title·원본 요약을 화면 모델로 매핑한다.
감정 필터는 같은 이름의 원본 감정 태그만 사용한다. 별도 자동 분류는 없다.
표시되는 이미지는 항목 소유권 확인 API의 서명 URL을 사용하며 만료 전에 다시 발급한다.
회원 변경과 화면 해제 때 진행 중 요청·서명 URL 상태는 폐기한다.

목록의 커서 및 이미지 접근 계약은 [그림일기·컬렉션 API](../engineering/diary-api.md)를 따른다.

## 더미 화면의 이전 검증 범위

`frontend/src/lib/collection.ts`의 CollectionRepository는 목록·상세의 읽기 인터페이스다.
화면은 저장소와 독립적인 controller를 사용하며 계정 ID 변경 시 controller와 조회 상태를
새로 만든다. 로그아웃 때 보호 화면이 해제되면 이전 상태도 버린다. 조회 세대와
AbortSignal로 이전 요청·취소된 상세·폐기된 계정의 늦은 응답을 무시한다.

CollectionItem은 ID·날짜·제목·이미지 표시 정보·분류를, CollectionDetail은 위로 문구·
마음·고민 목록·감정을 추가한다. 회원 ID는 로그인 상태에서 가져오며
모든 로그인 회원에게 동일한 더미 목록과 상세를 제공한다. 더미 기록에 회원 ID를 저장하거나
로컬 seed의 고정 회원 ID로 필터링하지 않는다.
이 모델은 DB 스키마나 확정된 서버 API가 아니다.

실제 DB/API에 연결하지 않는다. 더미 자료는 브라우저 번들에 포함된 공통 예시 콘텐츠다.
실제 연동 시 서버에서 세션·소유권·비공개 이미지 권한을
검사하고 공용 `apiFetch("/api/v1/...")`와 응답 규격을 사용해야 한다.

로컬 테스트 계정과 배포 환경에서 가입한 계정 모두 같은 8개 기록을 제공한다.
PC는 첫 6개와 다음 2개로 나뉘며, 모든 계정에서 목록의 같은 ID로 상세를 열 수 있다.
회원 변경 시 화면 상태 초기화와 이전 요청 폐기는 유지한다. 비회원은 로그인 화면으로 이동한다.
정상 0건은 아래 개발용 `empty` 시나리오로 확인한다.

개발 서버에서만 `collectionPreview` 쿼리로 모의 응답을 재현한다.
로그인을 생략하지 않으며 운영 빌드에서는 쿼리를 무시한다.

| URL | 동작 |
| --- | --- |
| `/collection?collectionPreview=empty` | 정상 0건 |
| `/collection?collectionPreview=error` | 첫 목록 실패, 재시도 성공 |
| `/collection?collectionPreview=detail-error` | 첫 상세 실패, 재시도 성공 |
| `/collection?collectionPreview=slow` | 목록·상세 응답을 2.5초 지연 |

## Figma와 자산

- [PC 목록](https://www.figma.com/design/t66NuRwO9mgwGbLTc2allQ?node-id=84-936)
- [모바일 목록](https://www.figma.com/design/t66NuRwO9mgwGbLTc2allQ?node-id=84-1065)
- [PC 상세](https://www.figma.com/design/t66NuRwO9mgwGbLTc2allQ?node-id=107-5086)
- [모바일 상세](https://www.figma.com/design/t66NuRwO9mgwGbLTc2allQ?node-id=107-4584)

`frontend/public/images/collection/`의 필름·하트·새싹·구름·닫기·잎·편집 아이콘은
Figma 제공 원본 SVG다. SVG 루트 크기를 보존하고 wrapper와 transform으로 표시 크기를
맞춘다. 필름 곡선에 놓인 카드·구멍만 원본 좌표계로 배치하고 컨테이너 너비에 맞게
축소한다. 나머지 UI는 flex·grid를 사용한다.

`reference.png`는 Figma 카드의 ‘Source image / clipped’ 더미 사진 원본이다.
84:893~918의 Photo / Reference crop 좌표로 **사진 영역만** 보여준다.
전체 디자인 스크린샷을 UI로 표시하지 않으며 제목·날짜·필터·요약·버튼은 실제 요소다.
모바일 상세는 선택 기록의 동적 이미지와 제목을 사용한다. 실제 연동 시 이미지 표시 정보를
API 이미지로 교체한다. 기존 공용 배경·메뉴 아이콘·온글잎 콘콘체는 재사용한다.

## 검증

`npm --prefix frontend test`의 collection.test.mjs는 서로 다른 회원 ID의 동일 목록·상세, 미존재 ID,
정상 0건과 실패 구분·재시도, 6개 탐색 경계, 필터·팝업 복귀, 빠른 선택과 늦은 응답,
계정 상태 폐기 이후 응답 무시를 확인한다.
프론트 변경에는 lint와 typecheck도 수행한다.

2026-10-06 공통 더미 전환 후 lint·typecheck와 프론트 테스트 26개를 통과했다.
로컬 seed의 세 회원 ID와 임의의 신규 회원 ID에서 동일한 8개 목록을 제공하며,
서로 다른 회원 ID로 각 목록 기록의 상세를 조회할 수 있음을 회귀 테스트로 확인했다.

2026-10-06 초기 화면 구현 시 로컬 개발 서버에서 다음을 확인했다.

- lint·typecheck와 프론트 테스트 26개(컬렉션 회귀 테스트 6개 포함) 통과.
- 비회원 → 로컬 계정 로그인 → 컬렉션 복귀.
- PC 6개 표시·다음 2개 탐색·선택 기록 요약·닫기/Escape 후 위치·포커스 복귀.
- 모바일 390×844의 2열 목록·감정 필터·전체 화면 상세·아이콘/브라우저 뒤로가기,
  반복 선택 시 요약 연결과 목록 스크롤 복원.
- 정상 0건과 목록/상세 조회 오류 구분, 재시도 후 복구, 털어놓기 링크.
- 768×1024의 가로 넘침 없음, PC 기본 1280×720과 모바일 자산 표시.
- 변경 문서의 상대 링크와 Git diff 공백 오류 없음.

실제 저장 결과·서버 소유권 검사·DB/API 연동·대화 재개·운영 환경은 검증 대상이 아니다.

[공용 화면](shared-ui.md) · [문서 목록](../README.md)
