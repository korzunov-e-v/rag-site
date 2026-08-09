from typing import Annotated
from pathlib import Path
import shutil

from fastapi import Depends, HTTPException, status, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.v1.router import v1_router
from backend.app.api.v1.schemas import DocumentResponse
from backend.app.db.connect import get_db
from backend.app.db.models.document import Document


@v1_router.post("/documents", response_model=DocumentResponse)
def post_document(
    document: UploadFile,
    db: Annotated[Session, Depends(get_db)],
) -> Document:
    storage_dir: Path | None = None

    try:
        filename = document.filename

        db_document = Document(
            filename=str(filename),
            content_type=str(document.content_type),
            size=document.size,
            storage_path="",
        )
        db.add(db_document)
        db.flush()

        uploads_dir = Path("./uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)

        storage_dir = uploads_dir / str(db_document.id)
        storage_path = storage_dir / "original"
        storage_dir.mkdir(parents=True, exist_ok=True)
        with storage_path.open("wb") as buffer:
            shutil.copyfileobj(document.file, buffer)

        db_document.storage_path = str(storage_path)
        db.commit()
    except Exception as error:
        db.rollback()
        if storage_dir is not None:
            shutil.rmtree(storage_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document",
        ) from error

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
