from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.embeddings import create_embedding
from backend.app.services.retrieval import search_chunks


async def search_documents(
    query: str,
    db: AsyncSession,
    user_id: int,
):
    query_embedding = await create_embedding(query)

    return [
        {
            "id": chunk.id,
            "text": chunk.text,
            "distance": distance,
        }
        for chunk, distance in await search_chunks(
            query=query,
            query_embedding=query_embedding,
            db=db,
            user_id=user_id,
        )
    ]
