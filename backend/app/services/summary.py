from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Document, DocumentChunk
from backend.app.llm.openrouter import client
from backend.app.settings import settings

# Для краткого описания хватает начала документа.
SUMMARY_CONTEXT_CHARS = 6000
SUMMARY_MAX_LENGTH = 500

SUMMARY_PROMPT = """
Опиши, о чём документ, ОДНИМ предложением на русском языке (до 200 символов).
Без списков, заголовков и Markdown. Не начинай со слов «Документ», «Текст»
или «Этот документ».
"""


async def summarize_document(document: Document, db: AsyncSession) -> str | None:
    chunks = await db.scalars(
        select(DocumentChunk.text)
        .where(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
    )

    context = ""
    for text in chunks:
        if len(context) >= SUMMARY_CONTEXT_CHARS:
            break
        context += text + "\n\n"

    if not context:
        return None

    response = await client.chat.completions.create(
        model=settings.openrouter_llm_model,
        max_tokens=150,
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {
                "role": "user",
                "content": f"Файл: {document.filename}\n\n{context[:SUMMARY_CONTEXT_CHARS]}",
            },
        ],
    )

    return shorten(response.choices[0].message.content or "")


def shorten(text: str) -> str | None:
    # Модели не всегда соблюдают ограничение длины: берём первый абзац
    # и режем по концу предложения или слова, а не посреди слова.
    text = " ".join(text.strip().split("\n\n")[0].split())

    if len(text) <= SUMMARY_MAX_LENGTH:
        return text or None

    text = text[:SUMMARY_MAX_LENGTH]
    sentence_end = max(text.rfind(". "), text.rfind("! "), text.rfind("? "))

    if sentence_end > SUMMARY_MAX_LENGTH // 2:
        return text[:sentence_end + 1]

    return text.rsplit(" ", 1)[0] + "…"
