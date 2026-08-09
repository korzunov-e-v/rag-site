from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import DocumentChunk
from backend.app.settings import settings


def search_chunks(
    query_embedding: list[float],
    db: Session,
    limit: int = 5,
) -> list[DocumentChunk]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    statement = (
        select(DocumentChunk, distance.label("distance"))
        .where(distance <= settings.max_distance)
        .order_by(distance)
        .limit(limit)
    )

    return db.execute(statement).all()
