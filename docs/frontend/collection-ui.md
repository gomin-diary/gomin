# 컬렉션 조회 화면

로그인 회원이 실제 DB에 저장한 본인의 그림일기를 `/collection`에서 조회한다.
[그림일기 MVP](../engineering/diary-mvp.md)의 이미지 생성·컬렉션 저장과 연결한다.

## 조회와 화면

- AuthGuard와 공용 세션을 재사용한다. 서버가 세션으로 소유자를 결정하며 회원 ID를 요청에 보내지 않는다.
- `GET /api/v1/collection`으로 저장 항목 목록을 한 번 조회한다. 더미 자료는 테스트에서만 사용한다.
- 최신 저장 순서로 표시하며 PC 필름은 기존 6개 단위 이동, 모바일은 2열 목록이다.
- 전체·기쁨·슬픔·불안·관계·일상 필터는 요약의 감정 태그와 일치하는 값을 사용한다.
- 정상 0건·목록 조회 실패·로딩을 구분한다. 실패하면 다시 조회할 수 있다.
- 계정 변경 시 화면 상태를 초기화하고 취소되거나 이전 계정에서 시작한 응답은 폐기한다.
- 실제 생성 이미지를 object-fit으로 표시한다. 서명 URL이 만료되면 화면을 다시 조회한다.

목록 저장소는 `frontend/src/lib/collection-api.ts`, 화면 상태와 탐색은 기존 `collection.ts`의 controller를 사용한다.
서버 페이지네이션이나 별도 이미지 URL 조회·갱신 타이머는 추가하지 않는다.

## 상세 화면

선택은 `#entry=<항목 UUID>`로 표시한다. PC는 팝업, 모바일은 전체 화면 상세를 유지한다.
닫기·Escape·브라우저 뒤로가기 후 목록 위치와 필터로 복귀한다.
`GET /api/v1/collection/{entry_id}`로 본인의 저장 항목과 원본 요약을 조회한다.
제목·위로·지금의 마음·주요 고민·감정 순서를 그대로 표시하며 모바일에는 생성 이미지를 함께 표시한다.
타인 또는 없는 항목은 같은 404로 처리한다. 상세 실패 시 다시 조회할 수 있다.

‘이 이야기 이어서 보기’는 준비 중 안내를 유지한다. 대화 재개·검색·수정·삭제·공개 공유는 MVP에서 제외한다.

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

기존 collection controller 테스트와 실제 API 저장소 테스트로 목록 변환·0건·실패·계정 상태 폐기를 확인한다.
프론트 변경에는 lint와 typecheck를 수행한다. 실제 제공자 생성과 운영 DB 적용은 별도 확인이 필요하다.

[공용 화면](shared-ui.md) · [문서 목록](../README.md)
