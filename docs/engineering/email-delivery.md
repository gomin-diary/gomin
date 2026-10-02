# SMTP·Resend 이메일 발송

백엔드의 `app.mail`은 공통 `Mailer` 인터페이스 아래 `SmtpMailer`와
`ResendMailer` 구현을 제공한다. `get_mailer()`는 `MAIL_PROVIDER` 설정에 맞는
구현을 반환한다. 기본값은 `resend`다. Render Free 웹 서비스는 SMTP용
25·465·587번 포트 outbound 연결을 차단하므로 해당 환경에서는 Resend를 사용한다. [Render 제한](https://render.com/docs/free#other-limitations)과
[Resend API](https://resend.com/docs/api-reference/introduction)를 참고한다.

인증번호 생성·저장·만료·검증, 재발송 제한과 회원가입 API는 호출하는 쪽에서
구현한다. Resend는 메일 전달만 담당하며 인증 제공자는 FastAPI다.

## 환경변수와 발신 도메인

`backend/.env.example`의 설정 이름을 사용한다. 실제 키는 서버 환경에만 등록하고
프론트엔드, 저장소, 로그, Jira에 기록하지 않는다. 프로세스 환경변수가 파일보다
우선한다. `MAIL_PROVIDER=resend`이면 Resend 설정을, `MAIL_PROVIDER=smtp`이면
기존 SMTP 설정을 사용한다. 선택하지 않은 구현으로 자동 전환하지 않는다.

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `MAIL_PROVIDER` | `resend` | `resend` 또는 `smtp` |
| `RESEND_API_KEY` | 빈 값 | 서버 전용 Resend API 키 |
| `RESEND_FROM_EMAIL` | 빈 값 | 검증된 소유 도메인의 발신 이메일 주소 |
| `RESEND_FROM_NAME` | `Gomin` | 수신자에게 표시할 발신자 이름 |
| `RESEND_TIMEOUT_SECONDS` | `10` | HTTP 작업 제한 시간, 0초 초과·60초 이하의 유한값 |

SMTP를 선택할 때는 다음 기존 설정을 사용한다.

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP 서버 |
| `SMTP_PORT` | `587` | `587`: STARTTLS, `465`: 연결 시작부터 TLS |
| `SMTP_USERNAME` | 빈 값 | SMTP 계정 이메일, 발신 주소로 사용 |
| `SMTP_PASSWORD` | 빈 값 | 서버 전용 Google 앱 비밀번호 |
| `SMTP_FROM_NAME` | `Gomin` | 표시할 발신자 이름 |
| `SMTP_TIMEOUT_SECONDS` | `10` | SMTP 작업 제한 시간, 0초 초과·60초 이하 |

Google SMTP는 계정의 2단계 인증과 앱 비밀번호를 사용한다.
[Google 앱 비밀번호 안내](https://support.google.com/mail/answer/185833?hl=ko)를 참고한다.
SMTP TLS 연결·인증·수신자 거절 처리와 별도 스레드 실행을 유지한다.

Resend 설정 절차는 다음과 같다.

1. Resend에서 소유한 `gomin.today` 또는 발송용 하위 도메인을 추가한다.
2. Resend가 제시하는 DNS 레코드를 도메인 DNS 관리 화면에 등록하고 검증 완료를 확인한다. 실제 레코드 값은 Resend 화면을 따른다.
3. 해당 발신 도메인에 사용할 API 키를 발급하고 발신 주소를 결정한다.
4. Render 백엔드 Environment에 위 서버 설정을 등록하고 재배포한다.
5. 통제된 테스트 수신함으로 발송하여 API 접수 ID와 실제 수신을 각각 확인한다.

도메인 등록·키 발급·Render 설정은 코드 반영만으로 완료되지 않는다.
[Resend 도메인 안내](https://resend.com/docs/dashboard/domains/introduction)를 참고한다.
메일 설정이 비어 있어도 상태 API는 시작할 수 있지만 메일 발송은
`MailConfigurationError`로 실패한다. 설정 변경 후 서버를 재시작한다.

## 호출 예시

```python
from app.mail import get_mailer

mailer = get_mailer()

# 일반 발송은 수신자·제목·본문만 전달하면 된다. 발신 주소는 서버 설정을 사용한다.
email_id = await mailer.send_email("member@example.com", "메일 제목", "일반 텍스트 본문")

# 동일 발송을 재시도하는 호출자는 저장한 요청 ID를 명시한다.
email_id = await mailer.send_verification_email(
    "member@example.com",
    code="123456",  # 예시값. 생성·검증·만료는 호출자가 관리한다.
    idempotency_key="signup-verification/<persisted-request-id>",
    expires_minutes=3,
)

email_id = await mailer.send_email(
    "member@example.com",
    subject="메일 제목",
    text="일반 텍스트 본문",
    html="<p>HTML 본문</p>",
    idempotency_key="notification/<persisted-request-id>",
)
```

FastAPI에서는 `mailer: Mailer = Depends(get_mailer)`로 주입한다.
호출자는 같은 `send_email(to, subject, text)`를 사용하고 구현을 구분할 필요가 없다.
Resend는 HTTPX 비동기 클라이언트를, SMTP는 별도 스레드에서 TLS 연결을 사용한다.
연결 생성·인증·정리는 각 구현 내부에서 수행하며 호출자가 연결 객체를 전달하지 않는다.
Resend는 API 접수 ID 문자열을 반환하고 SMTP는 수락 완료 시 `None`을 반환한다.
두 결과 모두 수신함 도착의 증거는 아니다.
HTML에 사용자 입력을 넣는 호출자는 해당 입력을 이스케이프해야 한다.

## 중복 방지와 실패 계약

SMTP는 제공자 중복 방지 키를 지원하지 않는다. 공통 인터페이스의
`idempotency_key`를 전달해도 SMTP에서는 중복 제거를 보장하지 않는다.
SMTP 발송 재시도는 호출자가 수락 결과와 중복 발송 가능성을 확인해서 결정한다.
SMTP 응답 거절은 확인된 실패로, 연결 끊김·타임아웃은 보수적으로 불명확한 결과로 전달한다.

다음 중복 방지 설명과 HTTP 상태 분류는 Resend 구현에 적용된다.

`idempotency_key`를 생략하면 모듈이 발송 호출마다 새로운 UUID를 생성한다.
자동 재시도는 없으며, 별도의 호출은 새 발송으로 취급한다. 같은 발송의 재시도를
관리하는 호출자는 저장한 요청 ID로 키를 명시해야 한다. 키는 공백 없는
ASCII 문자 1~256자로 제한한다. 코드·이메일·비밀값을 키에 넣지 않는다.
같은 발송을 재시도할 때는 **동일 키와 동일 본문**을 사용하고, 새 인증번호를
재발송하는 별도 요청에는 새 키를 사용한다. Resend의 중복 방지 보관 기간은
24시간이므로 그 이후 불명확한 발송을 무조건 재시도하지 않는다.
[Resend 중복 방지 안내](https://resend.com/docs/dashboard/emails/idempotency-keys)

모듈은 자동 재시도와 리다이렉트를 수행하지 않으며 오류 원문을 노출하지 않는다.

| 결과 | 전달 | 호출자의 처리 |
| --- | --- | --- |
| 설정 누락·잘못된 발신 설정 | `MailConfigurationError` | 운영 설정 수정, 발송 성공으로 처리하지 않음 |
| 잘못된 수신 주소·제목·코드·요청 키 | `ValueError` | 요청 검증 실패 처리 |
| 4xx 거절(409 제외), 연결 실패·연결/풀 타임아웃 | `MailDeliveryError(delivery_uncertain=False)` | 확인된 실패로 발송 한도 예약 해제 가능 |
| 409, 5xx, 리다이렉트, 전송/응답 오류·타임아웃, 잘못된 성공 응답 | `MailDeliveryError(delivery_uncertain=True)` | 이미 접수되었을 수 있으므로 한도 예약 유지, 동일 키·본문으로 조회/재시도 정책 적용 |

`status_code`는 HTTP 오류일 때만 제공하며 네트워크 오류에서는 `None`이다.
429는 발송 한도 또는 API 호출 제한이므로 제공자 설정·사용량을 확인한다.
409는 동일 키 요청이 처리 중인 경우를 포함하므로 보수적으로 불명확 상태로 취급한다.
[Resend 오류 안내](https://resend.com/docs/api-reference/errors)

호출자는 3분 코드 만료, 5회 입력 실패 시 무효화, 60초 재발송 대기,
이메일별 최근 1시간 최대 5회 발송 정책을 별도로 구현한다. 확인된 발송 실패는
한도에서 제외하지만 불명확한 결과를 확인된 실패로 간주하지 않는다.

## 검증

```sh
cd backend
.venv/bin/python -m unittest discover -s tests -v
```

테스트는 실제 환경 파일을 읽지 않고 HTTP·SMTP 전송 경계를 대체해 구현 선택,
SMTP TLS 연결·인증·스레드 실행, Resend 요청 형식,
메일 내용, 중복 방지 키, 비밀값 마스킹과 실패 분류를 검증한다.
발신 도메인 검증·Render 설정·실제 메일 수신은 해당 서비스에서 별도로 확인해야 한다.

[문서 목록](../README.md)
