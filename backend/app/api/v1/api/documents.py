from typing import Annotated
from pathlib import Path
import shutil

from fastapi import Depends, HTTPException, status, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.v1.router import v1_router
from backend.app.api.v1.schemas import DocumentResponse
from backend.app.db.connect import get_db
from backend.app.db.models import DocumentChunk
from backend.app.db.models.document import Document
from backend.app.llm.openrouter import client
from backend.app.services.chunking import split_text

from backend.app.services.embeddings import create_embedding, create_embeddings
from backend.app.services.extraction import get_text
from backend.app.services.retrieval import search_chunks
from backend.app.settings import settings

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
MAX_FILE_SIZE = 500 * 1024 * 1024
COPY_CHUNK_SIZE = 1024 * 1024


@v1_router.post("/documents", response_model=DocumentResponse)
def post_document(
    document: UploadFile,
    db: Annotated[Session, Depends(get_db)],
) -> Document:
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

    storage_dir: Path | None = None

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

    db.refresh(db_document)

    text = get_text(storage_path)
    if text is not None:
        print(len(text))
        print(filename)
        chunks = split_text(text)
        embeddings = create_embeddings(chunks)
        for chunk_index, chunk in enumerate(chunks):
            db_chunk = DocumentChunk(
                document_id=db_document.id,
                chunk_index=chunk_index,
                text=chunk,
                embedding=embeddings[chunk_index],
            )
            db.add(db_chunk)
        db.commit()

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
