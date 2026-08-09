from sqlalchemy.orm import Session

from backend.app.services.embeddings import create_embedding
from backend.app.services.retrieval import search_chunks


def search_documents(query: str, db: Session):
    query_embedding = create_embedding(query)

    return [
        {
            "id": chunk.id,
            "text": chunk.text,
            "distance": distance,
        }
        for chunk, distance in search_chunks(
            query_embedding=query_embedding,
            db=db,
        )
    ]
