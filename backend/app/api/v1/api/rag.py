from typing import Annotated
from collections import defaultdict


from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.api.v1 import v1_router
from backend.app.db.connect import get_db
from backend.app.llm.openrouter import client
from backend.app.services.ask import ask_documents
from backend.app.services.embeddings import create_embedding
from backend.app.services.retrieval import search_chunks
from backend.app.services.search import search_documents
from backend.app.settings import settings


@v1_router.post("/search")
async def search(
    query: str,
    db: Annotated[Session, Depends(get_db)],
):
    return await search_documents(query, db)


@v1_router.post("/ask")
async def ask(
    query: str,
    db: Annotated[Session, Depends(get_db)],
):
    return ask_documents(query, db)
