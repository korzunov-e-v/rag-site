import logging
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from backend.app.db.models import Document, User
from backend.app.services.storage import s3_storage

logger = logging.getLogger(__name__)


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".docx",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
}
MAX_FILE_SIZE = 500 * 1024 * 1024


def validate_file(filename: str | None, size: int | None) -> None:
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    if size is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size is required",
        )
    if size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must not be empty",
        )
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported formats: PDF, TXT, MD, DOCX, HTML, PNG, JPG",
        )

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size must not exceed 500 MB",
        )


async def store_document(
    file: BinaryIO,
    filename: str,
    content_type: str | None,
    size: int,
    current_user: User,
    db: AsyncSession,
) -> Document:
    validate_file(filename, size)

    try:
        db_document = Document(
            owner_id=current_user.id,
            filename=filename,
            content_type=content_type,
            size=size,
            storage_key="",
        )
        db.add(db_document)
        await db.flush()

        storage_key = f"documents/{db_document.id}/{filename}"

        await run_in_threadpool(
            s3_storage.upload,
            file,
            storage_key,
        )

        db_document.storage_key = storage_key

        await db.commit()
        await db.refresh(db_document)

        return db_document

    except Exception as error:
        await db.rollback()
        if "storage_key" in locals():
            await run_in_threadpool(s3_storage.delete, storage_key)
        logger.exception("Failed to upload document")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document",
        ) from error


async def save_document(document: UploadFile, current_user: User, db: AsyncSession) -> Document:
    return await store_document(
        document.file,
        document.filename,
        document.content_type,
        document.size,
        current_user,
        db,
    )
