from sqlalchemy import Text, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.app.db.models import DocumentChunk, Document
from backend.app.settings import settings

# Сглаживающая константа Reciprocal Rank Fusion из оригинальной статьи.
RRF_K = 60


def text_query(query: str):
    # plainto_tsquery соединяет слова через AND, и вопрос, где хоть одно слово
    # не встречается в тексте, не найдёт ничего. Меняем на OR, а ранжирование
    # поднимет чанки, где совпало больше слов.
    return func.to_tsquery(
        "russian",
        func.replace(
            cast(func.plainto_tsquery("russian", query), Text),
            "&",
            "|",
        ),
    )


async def vector_search(
    query_embedding: list[float],
    db: AsyncSession,
    user_id: int,
    limit: int,
) -> list[tuple[DocumentChunk, float]]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    statement = (
        select(DocumentChunk, distance)
        .join(Document)
        .options(joinedload(DocumentChunk.document))
        .where(Document.owner_id == user_id)
        .where(distance < settings.max_distance)
        .order_by(distance)
        .limit(limit)
    )

    result = await db.execute(statement)
    return result.all()


async def text_search(
    query: str,
    query_embedding: list[float],
    db: AsyncSession,
    user_id: int,
    limit: int,
) -> list[tuple[DocumentChunk, float]]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    ts_query = text_query(query)

    statement = (
        select(DocumentChunk, distance)
        .join(Document)
        .options(joinedload(DocumentChunk.document))
        .where(Document.owner_id == user_id)
        .where(DocumentChunk.search_vector.op("@@")(ts_query))
        .order_by(func.ts_rank_cd(DocumentChunk.search_vector, ts_query).desc())
        .limit(limit)
    )

    result = await db.execute(statement)
    return result.all()


async def search_chunks(
    query: str,
    query_embedding: list[float],
    db: AsyncSession,
    user_id: int,
    limit: int = 5,
) -> list[tuple[DocumentChunk, float]]:
    """Гибридный поиск: векторный + полнотекстовый, объединённые через RRF.

    Векторный поиск понимает смысл, но плохо находит точные термины, номера
    и коды; полнотекстовый — наоборот.
    """
    candidates = limit * 2

    rankings = [
        await vector_search(query_embedding, db, user_id, candidates),
        await text_search(query, query_embedding, db, user_id, candidates),
    ]

    scores: dict[int, float] = {}
    found: dict[int, tuple[DocumentChunk, float]] = {}

    for ranking in rankings:
        for rank, (chunk, distance) in enumerate(ranking, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1 / (RRF_K + rank)
            found[chunk.id] = (chunk, distance)

    best = sorted(scores, key=scores.get, reverse=True)[:limit]
    return [found[chunk_id] for chunk_id in best]
