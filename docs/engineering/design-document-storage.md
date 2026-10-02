# 설계문서 보관과 Jira 연결

설계문서의 로컬 작업본은 `docs/superpowers/plans/`에 보관하고 Git에서 제외한다. 팀이 검토하고 참조하는 공유본은 Confluence GOMIN 공간에 게시한 뒤 [설계문서 데이터베이스](https://younkim.atlassian.net/wiki/spaces/GOMIN/database/1474562)에 등록한다. 보관 규칙인 이 문서는 Git으로 관리한다.

## 로컬 작성 규칙

- 경로: `docs/superpowers/plans/YYYY-MM-DD-gomin-<번호>-<주제>.md`
- 파일명에는 실제 작성일, 대표 Jira 번호, 설계 주제를 사용한다.
- `.gitignore`의 `/docs/superpowers/plans/` 규칙을 유지하고 강제 추가하지 않는다. 이미 추적된 파일은 ignore만으로 제외되지 않으므로 추적 여부를 확인한다.
- 설계 수정과 구현을 구분한다. 설계를 게시했다고 구현 완료 또는 승인으로 기록하지 않는다.
- 비밀정보와 실제 환경변수 파일 내용을 설계에 포함하지 않는다.

문서 상단에 아래 정보를 작성한다.

| 항목 | 작성 내용 |
| --- | --- |
| 설계 대상 | 대표 Jira 키·작업 제목·이슈 링크 |
| 관련 작업 | 영향을 받는 Story/Task/Subtask의 키와 링크, 상위 Epic |
| 범위 | 이번 작업에서 구현할 내용과 후속으로 분리한 내용 |
| 상태 | 실제 검토·합의 상태. 새 제안은 `검토안` |
| 작성일·수정일 | 실제 날짜, 프로젝트 기준 Asia/Seoul |
| 로컬 경로 | 저장소 기준 상대 경로 |
| 공유본 | 게시 후 Confluence 페이지 링크 |
| 근거·검증 | 요구사항·Figma·코드 등 근거와 확인한 범위 |

## Confluence 게시와 데이터베이스 등록

1. 현재 Jira의 제목·유형·Parent·범위를 조회하고 대표 작업을 선택한다. 여러 작업에 걸친 공통 기반은 담당 Task를 대표로 하고 관련 Story/Subtask를 본문에 연결한다. 특정 하위 작업만을 위한 설계라면 해당 Subtask와 부모를 함께 적는다. Epic만 연결해서 구체적인 구현 작업을 생략하지 않는다.
2. 데이터베이스와 기존 페이지를 검색해 같은 작업·범위의 설계가 있는지 확인한다. 같은 설계의 수정은 기존 페이지를 갱신한다. 범위가 다른 문서는 별도 페이지로 만들고 관계를 설명한다.
3. Confluence GOMIN 공간의 **설계문서 데이터베이스 하위 페이지**로 `<대표 Jira 키> <설계 주제>` 제목의 공유본을 게시한다. 페이지 생성 시 부모를 설계문서 DB로 지정한다. 기존 페이지가 다른 위치에 있다면 DB 아래로 이동한다. 로컬 파일 경로는 코드 참조로 적고, 문서 간 링크는 공유 페이지 URL로 바꾼다.
4. 설계문서 DB에 아래 필드를 입력한다. 페이지 게시와 DB 행 등록은 별도 작업이므로 둘 다 완료해야 한다.
5. 게시 페이지와 DB를 다시 읽어 본문·관련 Jira·상태·작성일·링크가 저장됐는지 확인한다. 페이지의 부모가 설계문서 DB인지도 확인한다. DB 행에 링크를 등록하는 것만으로 페이지 위치가 이동하지는 않는다. 로컬 작업본에도 공유 페이지 URL을 기록한다.
6. 설계 수정 시 공유본·로컬 작업본·DB 상태를 맞추고 변경 이유를 남긴다. 기존 다른 문서나 DB 행은 보존한다. 문서 목록에는 공유본을 연결하고 Git에서 제외된 로컬 파일에 의존하지 않는다.

| 현재 DB 필드 | 유형 | 등록 기준 |
| --- | --- | --- |
| 문서명 | text | 대표 Jira 키와 설계 주제 |
| 설계 페이지 | confluence-page-link | 실제 게시한 Confluence 페이지 |
| 관련 Jira | jira-work-item | 대표 작업 이슈 링크. 추가 관련 작업은 본문에 명시 |
| 상태 | tag | 현재 사용하는 `검토안`을 기본으로 한다. 합의·승인은 근거가 있을 때만 반영 |
| 작성일 | date | 최초 작성일 `YYYY-MM-DD`; 수정일은 본문에 별도 기록 |

후속 작업의 전용 이슈가 아직 없으면 기존 관련 작업에 연결하고 본문에 **전용 Jira 이슈 미등록·작업 분리안**임을 적는다. 임의 이슈 키를 만들거나 기존 이슈가 분리됐다고 기록하지 않는다. Jira 이슈 생성·Parent 변경·상태 전환은 별도 요청 범위로 다룬다.

## 현재 Jira 구조

2026-10-02에 GOMIN 프로젝트의 이슈 목록, 실제 Parent, 이슈 유형 메타데이터와 설계문서 DB를 조회한 기록이다. 작업을 시작할 때는 최신 값을 다시 확인한다. 보드·스프린트·상태 전환 규칙을 정의한 문서는 아니다.

| 영역 / Epic | 확인된 직속 작업과 하위 구조 |
| --- | --- |
| [GOMIN-1 개발 환경 구축](https://younkim.atlassian.net/browse/GOMIN-1) | GOMIN-2~9 기술 기반 Task |
| [GOMIN-10 공용 화면 기반 구축](https://younkim.atlassian.net/browse/GOMIN-10) | GOMIN-12 네비게이션 Story → 17·18, GOMIN-13 배경 Task → 19·20 |
| [GOMIN-11 회원가입 및 로그인 제공](https://younkim.atlassian.net/browse/GOMIN-11) | GOMIN-14 공통 인증·세션 Task; GOMIN-15 회원가입 Story → 21·22·23; GOMIN-16 로그인 Story → 24·25·26; GOMIN-53 Resend 메일 발송 Task |
| [GOMIN-27 컬렉션](https://younkim.atlassian.net/browse/GOMIN-27) | GOMIN-28 접근·개인 기록 Story → 31·32; GOMIN-29 저장 목록 Story → 33·34; GOMIN-30 상세 Story → 35·36 |
| [GOMIN-52 털어놓기](https://younkim.atlassian.net/browse/GOMIN-52) | GOMIN-51 노트 유형 작업 |
| [GOMIN-50 공통 API 응답 모델](https://younkim.atlassian.net/browse/GOMIN-50) | Task, 조회 당시 Parent 없음 |

유형 선택은 [Jira 이슈 유형과 작업 분해 기준](jira-issue-guide.md)을 따른다. 실제 프로젝트 유형에서 `Subtask`(10034)는 `subtask=true`다. 이름이 비슷한 `하위 작업`(10039)은 `subtask=false`이므로 Subtask로 취급하지 않는다. `노트`(10040)도 별도 유형이다. 에픽(10035), 스토리(10036), 버그(10037), 작업(10038)은 `subtask=false`로 조회됐다. 이름만 보고 계층이나 유형을 변경하지 않는다.

[문서 목록](../README.md)
