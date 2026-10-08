import asyncio

from app.core.errors import AppError
from app.schemas.talk import SummaryContent
from app.talk.provider import TalkProvider
from app.talk.repository import TalkRepository


async def generate(repository: TalkRepository, provider: TalkProvider, member_id, conversation_id, job):
    """One bounded execution; no retry or fallback response. DB lease rejects late output."""
    output = None
    error_code = None
    try:
        async with asyncio.timeout(60):
            snapshot = await repository.snapshot(member_id, conversation_id)
            messages = [{"role": message["role"], "content": message["content"]}
                        for message in snapshot["messages"] if message["seq_no"] <= job["source_until_seq_no"]]
            if job["kind"] == "reply":
                content = await provider.reply(messages)
                if not isinstance(content, str) or not content.strip() or len(content) > 8000:
                    raise ValueError("Invalid reply")
                output = {"content": content}
            else:
                content = await provider.summarize(messages)
                summary = SummaryContent.model_validate(content)
                output = summary.model_dump()
    except TimeoutError:
        error_code = "AI_TIMEOUT"
    except AppError as error:
        # Internal dependency errors are never serialized verbatim.
        error_code = "AI_NOT_CONFIGURED" if error.code == "AI_NOT_CONFIGURED" else "AI_FAILED"
    except Exception:
        error_code = "AI_FAILED"
    try:
        await repository.complete(member_id, conversation_id, job, output, error_code)
    except AppError:
        # Database outage: no fake success. Lease expiry exposes failure on read.
        return
