from collections.abc import Awaitable, Callable

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.enums import MessageKind, MessageRole
from backend.app.db.models import Conversation, Message
from backend.app.services.agent import decide
from backend.app.services.ask import ask_documents

Emit = Callable[[str, dict], Awaitable[None]]

TITLE_LENGTH = 80
NOTHING_FOUND = "В документах не нашлось информации по этому вопросу."


async def get_conversation(
    db: AsyncSession,
    user_id: int,
    conversation_id: int | None,
    query: str,
) -> Conversation:
    if conversation_id is not None:
        conversation = await db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.owner_id == user_id,
            )
        )
        if conversation is not None:
            return conversation

    conversation = Conversation(owner_id=user_id, title=query[:TITLE_LENGTH])
    db.add(conversation)
    await db.flush()
    return conversation


async def handle_ask(
    db: AsyncSession,
    user_id: int,
    query: str,
    conversation_id: int | None,
    emit: Emit,
) -> None:
    conversation = await get_conversation(db, user_id, conversation_id, query)
    history = list(await db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id)
    ))

    db.add(Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        kind=MessageKind.QUESTION,
        content=query,
    ))
    await db.commit()

    await emit("ask:started", {"conversation_id": conversation.id})

    decision = await decide(query, history, db, user_id)

    if decision.action == "search":
        await emit("ask:searching", {"query": decision.text})

        answers = []
        async for result in ask_documents(decision.text, db, user_id):
            if "error" in result:
                await emit("document:error", {
                    "document_id": result["document_id"],
                    "filename": result["filename"],
                    "message": result["error"],
                })
                continue

            result = jsonable_encoder(result)
            answers.append(result)
            await emit("answer", result)

        if answers:
            reply = Message(
                role=MessageRole.ASSISTANT,
                kind=MessageKind.ANSWERS,
                content=decision.text,
                answers=answers,
            )
        else:
            reply = Message(
                role=MessageRole.ASSISTANT,
                kind=MessageKind.REPLY,
                content=NOTHING_FOUND,
            )
            await emit("reply", {"text": NOTHING_FOUND})

    else:
        kind = MessageKind.CLARIFICATION if decision.action == "clarify" else MessageKind.REPLY
        reply = Message(role=MessageRole.ASSISTANT, kind=kind, content=decision.text)
        await emit("clarification" if decision.action == "clarify" else "reply", {"text": decision.text})

    reply.conversation_id = conversation.id
    db.add(reply)
    conversation.updated_at = func.now()
    await db.commit()

    await emit("ask:finished", {"conversation_id": conversation.id})
