# UptimeRobot — 모니터링

UptimeRobot으로 운영 백엔드의 HTTP 응답을 외부에서 주기적으로 확인하고 이메일 알림을 받는다.

## 현재 운영 설정

| 항목 | 설정 |
| --- | --- |
| 대상 | 운영 백엔드 주소의 `/api/v1/health` |
| 확인 주기 | 5분 |
| 알림 채널 | 이메일 |

실제 백엔드 호스트와 알림 수신 연락처는 UptimeRobot 대시보드에서 관리한다. 인증 키나 세션 쿠키는 이 상태 API에 필요하지 않다.

## 확인 범위

[상태 라우터](../../backend/app/api/routes/health.py)의 `/api/v1/health`는 `GET`으로 정의되어 있으며 FastAPI가 요청에 응답할 수 있는지 확인한다. 정상 응답은 HTTP 200이며 공통 응답의 `data.status`는 `"ok"`다. UptimeRobot 모니터의 실제 요청 방식은 대시보드에서 별도로 확인한다.

이 경로는 DB 함수를 호출하거나 파일을 저장하지 않는다. 따라서 현재 모니터가 정상이어도 DB·Storage·메일 발송·프론트엔드 화면·로그인이 정상이라는 뜻은 아니다. DB 연결 확인은 [Supabase DB 운영](supabase-database.md)의 `/api/v1/health/db`를 사용하고, 나머지는 각 서비스의 배포 후 확인 절차를 따른다.

## 설정 유지와 변경

1. HTTP(s) 모니터의 대상이 실제 운영 백엔드 주소와 `/api/v1/health`인지 확인한다. 로컬 주소나 프론트엔드 주소를 넣지 않는다.
2. 백엔드의 `GET` 상태 API와 모니터의 요청 방식이 맞는지 확인한다. HTTP 모니터는 기본적으로 HEAD를 사용할 수 있으므로 Advanced Settings의 실제 설정을 확인하고, 필요한 경우 GET으로 맞춘다. [요청 방식에 따른 모니터 오류 확인](https://help.uptimerobot.com/en/articles/11358466-how-to-debug-a-monitor-showing-as-down-in-uptimerobot)
3. 확인 주기를 5분으로 맞추고 이메일 알림 연락처가 해당 모니터에 연결되어 있는지 확인한다.
4. 백엔드 도메인을 변경하면 모니터 URL도 갱신하고 새 주소의 응답을 확인한다.
5. 알림 지연·반복·타임아웃·모니터링 위치 등 추가 옵션은 대시보드의 실제 설정을 확인한다. 현재 문서의 5분 주기와 별도로 관리한다.

화면별 설정 방법은 [UptimeRobot 모니터 생성 안내](https://help.uptimerobot.com/en/articles/11358364-how-to-create-your-first-monitor-on-uptimerobot-quick-setup-guide)를 따른다. 응답과 모니터의 정상 판정 기준·재확인 결과에 따라 상태와 알림을 관리한다.

## 장애 알림을 받았을 때

1. 알림의 대상 URL·발생 시각·응답 상태를 확인하고 같은 경로의 실제 응답을 확인한다.
2. 미응답이나 서버 오류라면 [Render](render.md)의 배포 상태·Uvicorn 시작 로그·런타임 설정을 확인한다.
3. API는 응답하지만 기능이 실패하면 `/api/v1/health/db`와 해당 기능을 따로 확인한다. DB·Storage·메일 중 어느 경계에서 실패했는지 구분한다.
4. 복구 후 실제 요청과 UptimeRobot의 다음 확인 결과를 대조하고 이메일 알림의 수신 상태를 확인한다. 모니터 정상화만으로 전체 기능 복구를 확정하지 않는다.

[배포·운영 개요](README.md) · [문서 목록](../README.md)
