# 웹 개발 용어 사전

## 웹과 통신

| 용어 | 뜻 | 상세 문서 |
| --- | --- | --- |
| 인터넷 | 컴퓨터들이 데이터를 주고받도록 연결한 네트워크 | [웹 기초](web/web-basics.md) |
| 웹 | 인터넷 위에서 문서와 서비스를 제공하는 방식 | [웹 기초](web/web-basics.md) |
| 브라우저 | 웹 콘텐츠를 요청하고 화면에 표시하는 프로그램 | [웹 기초](web/web-basics.md) |
| 클라이언트 | 다른 프로그램에 서비스를 요청하는 쪽 | [웹 기초](web/web-basics.md) |
| 서버 | 요청을 받아 처리하는 프로그램 또는 그 프로그램이 실행되는 컴퓨터 | [웹 기초](web/web-basics.md) |
| HTTP | 클라이언트와 서버가 요청·응답을 주고받는 통신 규칙 | [HTTP](web/http.md) |
| HTTPS | TLS로 보호하는 HTTP 통신 | [HTTP](web/http.md) |
| TLS | 통신 암호화와 상대 신원 확인 등에 사용하는 보안 프로토콜 | [HTTP](web/http.md) |
| URL | 리소스에 접근할 위치와 방식을 나타내는 주소 | [HTTP](web/http.md) |
| 도메인 | 인터넷에서 대상을 구분할 때 사용하는 이름 | [배포 기초](deployment/deployment-basics.md) |
| DNS | 도메인 이름에 연결된 주소 등의 정보를 조회하는 시스템 | [HTTP](web/http.md) |
| 포트 | 한 컴퓨터에서 연결할 프로그램을 구분하는 번호 | [HTTP](web/http.md) |
| 헤더 | 요청·응답의 형식, 인증, 캐시 등 부가 정보를 담는 부분 | [HTTP](web/http.md) |
| 본문 | 요청·응답에서 실제 데이터를 담는 부분 | [HTTP](web/http.md) |
| 상태 코드 | 요청 처리 결과를 나타내는 HTTP 숫자 코드 | [HTTP](web/http.md) |
| JSON | 객체·배열 등의 데이터를 문자열로 표현하는 형식 | [HTTP](web/http.md) |

## API 설계

| 용어 | 뜻 | 상세 문서 |
| --- | --- | --- |
| API | 프로그램이 다른 기능을 사용할 때 따르는 접점과 사용 규칙 | [API 기초](api/api-basics.md) |
| HTTP API | HTTP 요청·응답으로 사용하는 API | [API 기초](api/api-basics.md) |
| 엔드포인트 | API에 요청을 보내는 접점. 메서드와 경로를 묶어 부르기도 함 | [API 기초](api/api-basics.md) |
| SDK | 특정 서비스나 기능을 쉽게 사용하도록 제공하는 개발 도구·라이브러리 묶음 | [API 기초](api/api-basics.md) |
| OpenAPI | HTTP API의 입력·응답 등을 명세하는 표준 형식 | [API 기초](api/api-basics.md) |
| Swagger UI | OpenAPI 명세를 화면에 표시하고 API 요청을 시험하는 도구 | [API 기초](api/api-basics.md) |
| REST | 리소스와 일관된 인터페이스 등을 중심으로 통신 구조를 설계하는 아키텍처 스타일 | [REST API](api/rest-api.md) |
| 리소스 | 회원이나 게시글처럼 API가 다루고 식별하는 대상 | [REST API](api/rest-api.md) |
| URI | 리소스를 식별하는 이름이나 주소. URL도 여기에 포함됨 | [REST API](api/rest-api.md) |
| CRUD | 데이터 생성·조회·수정·삭제를 묶어 부르는 말 | [REST API](api/rest-api.md) |
| 멱등성 | 같은 요청을 반복해도 의도한 최종 효과가 한 번 요청한 경우와 같은 성질 | [REST API](api/rest-api.md) |

## 애플리케이션과 인증

| 용어 | 뜻 | 상세 문서 |
| --- | --- | --- |
| 프론트엔드 | 화면 구성과 사용자 조작 등을 담당하는 영역 | [프론트엔드](application/frontend.md) |
| 백엔드 | 요청 검증과 데이터 처리, 응답 생성 등을 담당하는 영역 | [백엔드](application/backend.md) |
| 라이브러리 | 프로그램에서 가져다 쓰는 기능 묶음 | [프론트엔드](application/frontend.md) |
| 프레임워크 | 공통 기능과 프로그램의 기본 구조를 제공하는 틀 | [백엔드](application/backend.md) |
| 컴포넌트 | 화면을 구성하는 역할별 조각 | [프론트엔드](application/frontend.md) |
| 렌더링 | 데이터와 코드를 바탕으로 화면에 표시할 결과를 만드는 과정 | [프론트엔드](application/frontend.md) |
| 라우팅 | 경로 등을 페이지나 처리 함수에 연결하는 일 | [백엔드](application/backend.md) |
| 비동기 | 입출력 응답 등을 기다리는 동안 다른 작업을 진행하도록 구성하는 방식 | [백엔드](application/backend.md) |
| ASGI | Python 서버 프로그램과 웹 앱이 통신하는 호출 규칙 | [백엔드](application/backend.md) |
| 인증 | 요청한 사람이 누구인지 확인하는 일 | [인증과 인가](application/authentication.md) |
| 인가 | 사용자에게 특정 작업을 허용할지 판단하는 일 | [인증과 인가](application/authentication.md) |
| 쿠키 | 브라우저가 보관하고 조건에 맞는 요청에 함께 보내는 작은 데이터 | [인증과 인가](application/authentication.md) |
| 세션 | 여러 요청에 걸친 사용자의 상태를 관리하는 단위. 우리 로그인에서는 서버에 상태를 저장하고 식별자로 확인 | [인증과 인가](application/authentication.md) |
| 토큰 | 인증이나 권한 확인 등에 사용하는 값 | [인증과 인가](application/authentication.md) |
| JWT | 토큰을 표현하는 형식 중 하나 | [인증과 인가](application/authentication.md) |
| 해시 | 입력값에서 일정한 규칙으로 검증·식별용 값을 계산하는 방식 | [인증과 인가](application/authentication.md) |
| 출처 | 스킴·호스트·포트의 조합 | [CORS](application/cors.md) |
| CORS | 서버가 허용한 다른 출처의 접근 조건을 브라우저가 확인하는 방식 | [CORS](application/cors.md) |
| 프리플라이트 | 일부 다른 출처 요청을 보내기 전에 OPTIONS로 허용 조건을 확인하는 사전 요청 | [CORS](application/cors.md) |

## 데이터 저장

| 용어 | 뜻 | 상세 문서 |
| --- | --- | --- |
| 관계형 DB | 테이블과 관계로 데이터를 관리하는 데이터베이스 | [데이터베이스](data/database.md) |
| 테이블·행·열 | 데이터 묶음, 개별 기록, 기록의 속성 | [데이터베이스](data/database.md) |
| 스키마 | 데이터 구조와 규칙. PostgreSQL에서는 테이블 등을 묶는 이름 공간도 뜻함 | [데이터베이스](data/database.md) |
| 기본 키 | 테이블에서 한 행을 고유하게 식별하는 값 | [데이터베이스](data/database.md) |
| 외래 키 | 다른 테이블의 행을 참조하도록 연결하는 값 | [데이터베이스](data/database.md) |
| SQL | 관계형 DB에 조회·변경 등을 요청하는 언어 | [데이터베이스](data/database.md) |
| 인덱스 | 특정 조건의 조회를 빠르게 하도록 돕는 자료구조 | [데이터베이스](data/database.md) |
| 트랜잭션 | 여러 DB 작업을 함께 확정하거나 취소하도록 묶는 단위 | [데이터베이스](data/database.md) |
| RPC | 다른 곳에 있는 함수를 호출하는 방식 | [데이터베이스](data/database.md) |
| RLS | DB에서 행 단위 접근 규칙을 적용하는 기능 | [데이터베이스](data/database.md) |
| 마이그레이션 | DB 구조·권한 등의 변경을 버전별로 기록하고 적용하는 일 | [데이터베이스](data/database.md) |
| 버킷 | 파일 저장소에서 객체들을 묶고 저장 규칙을 설정하는 단위 | [Storage](data/storage.md) |
| 객체 경로 | 버킷 안에서 파일 객체를 구분하는 이름 | [Storage](data/storage.md) |
| 메타데이터 | 파일 크기나 형식처럼 데이터에 관한 정보 | [Storage](data/storage.md) |
| MIME 타입 | `image/png`처럼 데이터의 형식을 나타내는 이름 | [Storage](data/storage.md) |
| UUID | 식별자를 표현하는 형식. 우리 저장 모듈에서는 새 파일 경로를 만들 때 사용 | [Storage](data/storage.md) |
| 서명 URL | 정해진 조건과 시간 동안 파일 등에 접근하도록 허용하는 주소 | [Storage](data/storage.md) |

## 배포와 운영

| 용어 | 뜻 | 상세 문서 |
| --- | --- | --- |
| 의존성 | 프로그램이 사용하는 외부 라이브러리 등 | [배포 기초](deployment/deployment-basics.md) |
| 빌드 | 소스 코드를 배포할 결과물로 준비하는 과정 | [배포 기초](deployment/deployment-basics.md) |
| 배포 | 사용자에게 프로그램을 제공할 환경에 코드와 설정 등을 반영하는 일 | [배포 기초](deployment/deployment-basics.md) |
| 운영 환경 | 실제 사용자가 접속하는 서비스 환경 | [배포 기초](deployment/deployment-basics.md) |
| 환경변수 | 실행 환경이 프로그램에 전달하는 이름과 값 | [배포 기초](deployment/deployment-basics.md) |
| CI·CD | 자동 검사와 배포 준비·실행 등을 연결하는 흐름 | [배포 기초](deployment/deployment-basics.md) |
| CDN | 파일 등을 여러 위치에서 제공해 사용자까지의 전달 시간을 줄이는 네트워크 | [배포 플랫폼](deployment/platforms.md) |
| 로그 | 요청이나 오류처럼 개별 사건을 남긴 기록 | [모니터링](operations/monitoring.md) |
| 지표 | 응답 시간·오류 횟수처럼 상태를 수치로 모은 값 | [모니터링](operations/monitoring.md) |
| 상태 확인 API | 미리 정한 서비스 검사를 실행하고 결과를 응답하는 API | [모니터링](operations/monitoring.md) |
| 가용성 | 서비스를 사용할 수 있는 정도 | [모니터링](operations/monitoring.md) |

[목차](README.md)
