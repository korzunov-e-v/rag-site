from typing import Annotated

from fastapi import Depends, HTTPException, status, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.api.v1.router import v1_router
from backend.app.api.v1.schemas import DocumentResponse, DocumentResponsePre
from backend.app.db.connect import get_db
from backend.app.db.models import User
from backend.app.db.models.document import Document
from backend.app.services.storage import s3_storage

from backend.app.tasks.documents import process_document
from backend.app.services.save import save_document


@v1_router.post("/documents", response_model=DocumentResponse)
def post_document(
    document: UploadFile,
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> Document:
    db_document = save_document(document, current_user, db)
    process_document.delay(db_document.id)

    return db_document


@v1_router.get("/documents", response_model=list[DocumentResponse])
def get_documents(
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@v1_router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> Document:
    db_document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
        .first()
    )
    if db_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document(id={document_id}) not found",
        )
    return db_document


@v1_router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> None:
    db_document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
        .first()
    )

    if db_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document(id={document_id}) not found",
        )

    if db_document.storage_key:
        s3_storage.delete(db_document.storage_key)

    db.delete(db_document)
    db.commit()

