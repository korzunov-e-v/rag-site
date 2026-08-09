from typing import Annotated

from fastapi import Depends, HTTPException, status, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.v1.router import v1_router
from backend.app.api.v1.schemas import DocumentResponse
from backend.app.db.connect import get_db
from backend.app.db.models.document import Document
from backend.app.llm.openrouter import client

from backend.app.services.embeddings import create_embedding
from backend.app.services.process_doc import process_doc
from backend.app.services.retrieval import search_chunks
from backend.app.services.save import save_document
from backend.app.settings import settings



@v1_router.post("/documents", response_model=DocumentResponse)
def post_document(
    document: UploadFile,
    db: Annotated[Session, Depends(get_db)],
) -> Document:
    db_document = save_document(document, db)
    process_doc(db_document, db)

    return db_document


@v1_router.get("/documents", response_model=list[DocumentResponse])
def get_documents(
    db: Annotated[Session, Depends(get_db)],
) -> list[Document]:
    return list(db.scalars(select(Document)).all())


@v1_router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Document:
    db_document = db.scalar(
        select(Document).where(Document.id == document_id)
    )
    if db_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document(id={document_id}) not found",
        )
    return db_document


@v1_router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    db_document = db.scalar(
        select(Document).where(Document.id == document_id)
    )
    if db_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document(id={document_id}) not found",
        )
    db.delete(db_document)
    db.commit()
    return None


@v1_router.post("/search")
def search(
    query: str,
    db: Annotated[Session, Depends(get_db)],
):
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
