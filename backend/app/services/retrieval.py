from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.app.db.models import DocumentChunk, Document
from backend.app.settings import settings


async def search_chunks(
    query_embedding: list[float],
    db: AsyncSession,
    user_id: int,
    limit: int = 5,
) -> list[DocumentChunk]:
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
