"""Агент, который решает, что делать с сообщением пользователя.

Перед поиском LLM смотрит на историю диалога и список документов и выбирает
один инструмент: искать в документах (с запросом, переписанным так, чтобы он
был понятен без истории), переспросить или ответить сразу.
"""
import json
import logging
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.enums import MessageKind
from backend.app.db.models import Document, Message
from backend.app.llm.openrouter import client
from backend.app.settings import settings

logger = logging.getLogger(__name__)

HISTORY_MESSAGES = 10
MAX_DOCUMENTS_IN_PROMPT = 30

AGENT_PROMPT = """
Ты — помощник в системе поиска ответов по документам пользователя.
По истории диалога и новому сообщению выбери ровно один инструмент:

- search_documents — если для ответа нужно искать в документах. В query напиши
  самостоятельный поисковый вопрос на языке пользователя: раскрой местоимения
  и отсылки к предыдущим сообщениям («а на лопасти?» → «Какая гарантия на лопасти?»).
- ask_clarification — если по сообщению невозможно понять, что искать, даже
  с учётом истории.
- reply — если поиск не нужен: приветствие, благодарность, вопрос о том, что
  ты умеешь или какие документы загружены.

Если сомневаешься между поиском и чем-то другим — выбирай поиск.

Документы пользователя:
{documents}
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Найти ответ в документах пользователя",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Самостоятельный поисковый вопрос",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": "Задать пользователю уточняющий вопрос",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reply",
            "description": "Ответить пользователю без поиска по документам",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        },
    },
]


@dataclass
class Decision:
    action: Literal["search", "clarify", "reply"]
    text: str


def history_text(message: Message) -> str:
    if message.kind != MessageKind.ANSWERS or not message.answers:
        return message.content

    return "\n".join(
        f"{answer['filename']}: {answer['answer']}"
        for answer in message.answers
    ) or message.content


async def documents_text(db: AsyncSession, user_id: int) -> str:
    documents = await db.scalars(
        select(Document)
        .where(or_(Document.owner_id == user_id, Document.is_shared))
        .order_by(Document.created_at.desc())
        .limit(MAX_DOCUMENTS_IN_PROMPT)
    )

    lines = [
        f"- {document.filename}" + (f": {document.description}" if document.description else "")
        for document in documents
    ]
    return "\n".join(lines) or "(документов нет)"


async def decide(
    query: str,
    history: list[Message],
    db: AsyncSession,
    user_id: int,
) -> Decision:
    messages = [
        {
            "role": "system",
            "content": AGENT_PROMPT.format(documents=await documents_text(db, user_id)),
        },
        *(
            {"role": message.role.value, "content": history_text(message)}
            for message in history[-HISTORY_MESSAGES:]
        ),
        {"role": "user", "content": query},
    ]

    try:
        response = await client.chat.completions.create(
            model=settings.openrouter_llm_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="required",
        )
        call = response.choices[0].message.tool_calls[0]
        arguments = json.loads(call.function.arguments)

        match call.function.name:
            case "search_documents":
                return Decision("search", arguments["query"].strip() or query)
            case "ask_clarification":
                return Decision("clarify", arguments["question"])
            case "reply":
                return Decision("reply", arguments["text"])

    except Exception:
        # Агент — надстройка: если он не справился, просто ищем по исходному вопросу.
        logger.exception("Agent failed, falling back to search")

    return Decision("search", query)
