import shutil
from pathlib import Path

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from backend.app.db.models import Document

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
MAX_FILE_SIZE = 500 * 1024 * 1024
COPY_CHUNK_SIZE = 1024 * 1024


def validate_document(document: UploadFile) -> None:
    filename = document.filename
    extension = Path(filename).suffix.lower() if filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF, TXT and DOCX files are allowed",
        )

    if document.size is not None and document.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size must not exceed 500 MB",
        )


def save_document(document: UploadFile, db: Session) -> Document:
    filename = document.filename
    extension = Path(filename).suffix.lower() if filename else ""
    storage_dir: Path | None = None

    validate_document(document)

    try:
        db_document = Document(
            filename=filename,
            content_type=str(document.content_type),
            size=0,
            storage_path="",
        )
        db.add(db_document)
        db.flush()

        uploads_dir = Path("./uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)

        storage_dir = uploads_dir / str(db_document.id)
        storage_path = storage_dir / f"original{extension}"
        storage_dir.mkdir(parents=True, exist_ok=True)
        actual_size = 0
        with storage_path.open("wb") as buffer:
            while chunk := document.file.read(COPY_CHUNK_SIZE):
                actual_size += len(chunk)
                if actual_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="File size must not exceed 500 MB",
                    )
                buffer.write(chunk)

        db_document.size = actual_size
        db_document.storage_path = str(storage_path)
        db.commit()
        return db_document
    except HTTPException:
        db.rollback()
        if storage_dir is not None:
            shutil.rmtree(storage_dir, ignore_errors=True)
        raise
    except Exception as error:
        db.rollback()
        if storage_dir is not None:
            shutil.rmtree(storage_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document",
        ) from error
