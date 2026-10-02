import re
from abc import ABC, abstractmethod


class Mailer(ABC):
    @abstractmethod
    async def send_email(
        self, to: str, subject: str, text: str, *, html: str | None = None,
        idempotency_key: str | None = None,
    ) -> str | None:
        """Send one message; success means provider acceptance, not inbox delivery."""
        raise NotImplementedError

    async def send_verification_email(
        self, to: str, code: str, *, idempotency_key: str | None = None, expires_minutes: int = 3,
    ) -> str | None:
        """Render a caller-provided six-digit code; do not issue or store it."""
        if not re.fullmatch(r"[0-9]{6}", code) or expires_minutes <= 0:
            raise ValueError("A six-digit verification code and positive expiry are required")
        return await self.send_email(
            to, "[Gomin] 회원가입 이메일 인증",
            f"회원가입 이메일 인증번호는 {code}입니다.\n"
            f"{expires_minutes}분 이내에 입력해주세요.\n\n"
            "회원가입을 요청하지 않았다면 이 메일을 무시해주세요.",
            idempotency_key=idempotency_key,
        )
