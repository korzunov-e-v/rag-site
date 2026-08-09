from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.v1.router import v1_router
from backend.app.api.v1.schemas import DocumentCreate, DocumentResponse
from backend.app.db.connect import get_db
from backend.app.db.models.document import Document


@v1_router.post("/documents", response_model=DocumentResponse)
def post_document(
    document: DocumentCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Document:
    db_document = Document(**document.model_dump())
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
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
