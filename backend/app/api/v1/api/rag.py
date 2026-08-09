from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.api.v1 import v1_router
from backend.app.db.connect import get_db
from backend.app.llm.openrouter import client
from backend.app.services.embeddings import create_embedding
from backend.app.services.retrieval import search_chunks
from backend.app.services.search import search_documents
from backend.app.settings import settings


@v1_router.post("/search")
def search(
    query: str,
    db: Annotated[Session, Depends(get_db)],
):
    return search_documents(query, db)


@v1_router.post("/ask")
def ask(
    query: str,
    db: Annotated[Session, Depends(get_db)],
):
    query_embedding = create_embedding(query)
    chunks = search_chunks(
        query_embedding=query_embedding,
        db=db,
        limit=5,
    )
    if not chunks:
        return "В загруженных документах не найдено информации по этому вопросу."
    resp = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": settings.system_prompt.format(
                    chunks=[chunk.text for chunk, _ in chunks],
                    query=query
                )
            },
            {"role": "user", "content": query}
        ],
        model=settings.openrouter_llm_model,
        stream=False,
    )
    return resp.choices[0].message.content
