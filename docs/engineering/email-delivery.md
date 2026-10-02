# Google SMTP 이메일 발송

백엔드의 `app.mail`은 이메일 발송만 담당한다. 인증번호 생성·저장·만료·검증,
재발송 제한과 회원가입 API는 호출하는 쪽에서 구현해야 한다.

## 환경변수

설정 항목은 `backend/.env.example`을 기준으로 관리한다. 로컬에서는 개발자가
`backend/.env`에 설정하고, 배포에서는 백엔드 호스팅 환경변수로 설정한다.
프로세스 환경변수가 파일보다 우선한다. 프론트엔드에 SMTP 설정을 전달하지 않는다.

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `SMTP_HOST` | `smtp.gmail.com` | Google SMTP 서버 |
| `SMTP_PORT` | `587` | `587`: STARTTLS, `465`: 연결 시작부터 TLS |
| `SMTP_USERNAME` | 빈 값 | 발송용 Google 계정의 전체 이메일 주소, 발신 주소로도 사용 |
| `SMTP_PASSWORD` | 빈 값 | Google 앱 비밀번호, 서버 전용 비밀값 |
| `SMTP_FROM_NAME` | `Gomin` | 수신자에게 표시할 발신자 이름 |
| `SMTP_TIMEOUT_SECONDS` | `10` | SMTP 소켓 작업의 제한 시간, 0초 초과·60초 이하 |

Google 계정에서 2단계 인증을 활성화한 후 앱 비밀번호를 발급한다. 일반 계정
비밀번호를 사용하지 않는다. 앱 비밀번호 옵션이 없는 조직 계정은 관리자의 정책을
확인해야 한다. Google 계정 비밀번호를 변경하면 앱 비밀번호가 취소될 수 있다.
자세한 조건은 [Google 앱 비밀번호 안내](https://support.google.com/mail/answer/185833?hl=ko),
SMTP 설정은 [Google SMTP 안내](https://support.google.com/a/answer/176600?hl=ko)를 참고한다.

SMTP 사용자명과 비밀번호가 비어 있어도 기존 API는 시작할 수 있다. 메일 발송을
호출하면 `MailConfigurationError`가 발생한다. 설정 변경 후 백엔드를 재시작한다.

## 호출 예시

백엔드 비동기 함수에서 다음과 같이 호출한다.

```python
from app.mail import get_mailer

mailer = get_mailer()
await mailer.send_verification_email(
    "member@example.com",
    code="123456",  # 예시값. 실제 코드와 만료 정책은 호출하는 쪽에서 관리한다.
    expires_minutes=10,
)

await mailer.send_email(
    "member@example.com",
    subject="메일 제목",
    text="일반 텍스트 본문",
    html="<p>HTML 본문</p>",  # 선택 사항. 사용자 입력은 호출하는 쪽에서 이스케이프한다.
)
```

FastAPI에서는 `mailer: SmtpMailer = Depends(get_mailer)`로 주입할 수 있다.
SMTP 통신은 별도 스레드에서 실행한다. 호출은 SMTP 서버가 메일을 수락한 뒤
완료되며, 수신함 도착을 보장하지는 않는다.

한 번에 수신자 한 명에게 발송한다. 발신자는 로그인 계정으로 고정하며 TLS
인증서를 검증한다. SMTP 인증·통신 실패나 수신자 거절은 `MailDeliveryError`로
전달하며 SMTP 원문 응답을 외부로 노출하지 않는다. 잘못된 수신 주소나 헤더는
`ValueError`로 처리한다. 호출하는 쪽은 이를 적절한 API 응답으로 변환해야 한다.
자동 재시도는 없으며, 통신 실패 시 이미 발송되었을 가능성이 있으므로 재시도
정책은 호출하는 쪽에서 결정한다.

## 검증

백엔드 의존성이 설치된 환경에서 실행한다.

```sh
cd backend
.venv/bin/python -m unittest discover -s tests -p test_mail.py -v
```

테스트는 실제 환경 파일을 읽지 않고 SMTP 통신을 대체한다. TLS 연결 방식,
메일 내용, 환경변수 설정, 비밀값 마스킹과 실패 처리를 확인한다. 실제 Google
SMTP 인증과 수신 여부는 개발자가 발송 계정을 설정한 후 별도로 확인한다.

[문서 목록](../README.md)
