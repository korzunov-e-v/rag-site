import shutil
from pathlib import Path

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from backend.app.db.models import Document, User
from backend.app.services.storage import s3_storage
import logging

logger = logging.getLogger(__name__)


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
MAX_FILE_SIZE = 500 * 1024 * 1024
COPY_CHUNK_SIZE = 1024 * 1024


def validate_document(document: UploadFile) -> None:
    filename = document.filename

    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    if document.size is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size is required",
        )
    if document.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must not be empty",
        )
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF, TXT and DOCX files are allowed",
        )

    if document.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size must not exceed 500 MB",
        )


def save_document(document: UploadFile, current_user: User, db: Session) -> Document:
    filename = document.filename
    validate_document(document)

    try:
        db_document = Document(
            owner_id=current_user.id,
            filename=document.filename,
            content_type=document.content_type,
            size=document.size,
            storage_key="",
        )
        db.add(db_document)
        db.flush()

        storage_key = f"documents/{db_document.id}/{filename}"

        s3_storage.upload(
            document.file,
            storage_key,
        )

        db_document.storage_key = storage_key

        db.commit()
        db.refresh(db_document)

        return db_document

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()
        if "storage_key" in locals():
            s3_storage.delete(storage_key)
        logger.exception("Failed to upload document")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document",
        ) from error
