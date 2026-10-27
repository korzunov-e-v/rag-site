from datetime import datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.api.dependencies import get_current_user
from backend.app.api.v1.router import v1_router
from backend.app.api.v1.schemas import Model
from backend.app.db.connect import get_db
from backend.app.db.models import Conversation, User


class ConversationResponse(Model):
    id: int
    title: str
    updated_at: datetime


class MessageResponse(Model):
    id: int
    role: str
    kind: str
    content: str
    answers: list[dict] | None
    created_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]


async def get_own_conversation(
    conversation_id: int,
    db: AsyncSession,
    current_user: User,
) -> Conversation:
    conversation = await db.scalar(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.owner_id == current_user.id,
        )
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation(id={conversation_id}) not found",
        )
    return conversation


@v1_router.get("/conversations", response_model=list[ConversationResponse])
async def get_conversations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> list[Conversation]:
    result = await db.scalars(
        select(Conversation)
        .where(Conversation.owner_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    return list(result)


@v1_router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    conversation_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> Conversation:
    return await get_own_conversation(conversation_id, db, current_user)


@v1_router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> None:
    conversation = await get_own_conversation(conversation_id, db, current_user)

    await db.delete(conversation)
    await db.commit()
