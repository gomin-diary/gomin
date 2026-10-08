"""Provider-neutral boundary. No production mock or guessed provider/model."""

from typing import Protocol

from fastapi import Request

from app.core.errors import AppError
from app.schemas.talk import SummaryContent


class TalkProvider(Protocol):
    async def reply(self, messages: list[dict]) -> str: ...

    async def summarize(self, messages: list[dict]) -> SummaryContent: ...


class UnconfiguredTalkProvider:
    async def reply(self, messages: list[dict]) -> str:
        raise AppError(503, "AI_NOT_CONFIGURED", "모리 응답 서비스를 아직 연결하지 못했어요.")

    async def summarize(self, messages: list[dict]) -> SummaryContent:
        raise AppError(503, "AI_NOT_CONFIGURED", "요약 서비스를 아직 연결하지 못했어요.")


def get_talk_provider(request: Request) -> TalkProvider:
    return getattr(request.app.state, "talk_provider", UnconfiguredTalkProvider())
