from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends

from app.auth.session import require_member
from app.schemas.auth import MemberData
from app.schemas.response import ApiSuccess
from app.schemas.talk import (AcceptedMessage, ConfirmedSummaryHandoff, ConversationData,
                              JobData, MessageInput, SummaryData, SummaryInput)
from app.talk.provider import TalkProvider, get_talk_provider
from app.talk.repository import TalkRepository, get_talk_repository
from app.talk.service import generate

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])
Member = Annotated[MemberData, Depends(require_member)]
Repository = Annotated[TalkRepository, Depends(get_talk_repository)]
Provider = Annotated[TalkProvider, Depends(get_talk_provider)]


def handoff(data: dict) -> ConfirmedSummaryHandoff:
    summary = SummaryData(**data)
    return ConfirmedSummaryHandoff(conversation_id=summary.conversation_id, summary_id=summary.id,
                                   version=summary.version, summary=summary)


@router.post("", response_model=ApiSuccess[ConversationData], status_code=201)
async def create(member: Member, repository: Repository):
    return ApiSuccess(data=ConversationData(**await repository.create(member.id)))


@router.get("/{conversation_id}", response_model=ApiSuccess[ConversationData])
async def read(conversation_id: UUID, member: Member, repository: Repository):
    return ApiSuccess(data=ConversationData(**await repository.snapshot(member.id, conversation_id)))


@router.post("/{conversation_id}/messages", response_model=ApiSuccess[AcceptedMessage], status_code=202)
async def send(conversation_id: UUID, payload: MessageInput, background: BackgroundTasks,
               member: Member, repository: Repository, provider: Provider):
    accepted = await repository.send(member.id, conversation_id, payload)
    if accepted["execute"]:
        background.add_task(generate, repository, provider, member.id, conversation_id, accepted["job"])
    return ApiSuccess(data=AcceptedMessage(**accepted))


@router.post("/{conversation_id}/summaries", response_model=ApiSuccess[JobData], status_code=202)
async def summarize(conversation_id: UUID, payload: SummaryInput, background: BackgroundTasks,
                    member: Member, repository: Repository, provider: Provider):
    accepted = await repository.start_summary(member.id, conversation_id, payload.request_id)
    if accepted["execute"]:
        background.add_task(generate, repository, provider, member.id, conversation_id, accepted["job"])
    return ApiSuccess(data=JobData(**accepted["job"]))


@router.post("/{conversation_id}/resume", response_model=ApiSuccess[ConversationData])
async def resume(conversation_id: UUID, member: Member, repository: Repository):
    return ApiSuccess(data=ConversationData(**await repository.resume(member.id, conversation_id)))


@router.post("/{conversation_id}/summaries/{summary_id}/confirm", response_model=ApiSuccess[ConfirmedSummaryHandoff])
async def confirm(conversation_id: UUID, summary_id: UUID, member: Member, repository: Repository):
    return ApiSuccess(data=handoff(await repository.confirm(member.id, conversation_id, summary_id)))


@router.get("/{conversation_id}/summaries/{summary_id}/handoff", response_model=ApiSuccess[ConfirmedSummaryHandoff])
async def read_handoff(conversation_id: UUID, summary_id: UUID, member: Member, repository: Repository):
    return ApiSuccess(data=handoff(await repository.confirmed_summary(member.id, conversation_id, summary_id)))
