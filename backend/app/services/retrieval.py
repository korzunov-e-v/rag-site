from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import DocumentChunk, Document
from backend.app.settings import settings


def search_chunks(
    query_embedding: list[float],
    db: Session,
    user_id: int,
    limit: int = 5,
) -> list[DocumentChunk]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    statement = (
        select(DocumentChunk, distance)
        .join(Document)
        .where(Document.owner_id == user_id)
        .order_by(distance)
        .limit(limit)
    )

    return db.execute(statement).all()
