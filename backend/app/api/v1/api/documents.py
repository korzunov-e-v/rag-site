from typing import Annotated

from fastapi import Depends, HTTPException, status, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, require_admin
from backend.app.api.v1.router import v1_router
from backend.app.api.v1.schemas import DocumentFromUrl, DocumentResponse, DocumentUpdate
from backend.app.db.connect import get_db
from backend.app.db.models import User
from backend.app.db.models.document import Document
from backend.app.services.storage import s3_storage

from backend.app.tasks.documents import process_document
from backend.app.services.fetch_url import fetch_url
from backend.app.services.save import save_document, store_document


def visible_to(user: User):
    return or_(Document.owner_id == user.id, Document.is_shared)


async def get_visible_document(
    document_id: int,
    db: AsyncSession,
    current_user: User,
) -> Document:
    db_document = await db.scalar(
        select(Document).where(
            Document.id == document_id,
            visible_to(current_user),
        )
    )
    if db_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document(id={document_id}) not found",
        )
    return db_document


async def get_own_document(
    document_id: int,
    db: AsyncSession,
    current_user: User,
) -> Document:
    db_document = await get_visible_document(document_id, db, current_user)

    if db_document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Изменять документ может только его владелец",
        )
    return db_document


@v1_router.post("/documents", response_model=DocumentResponse)
async def post_document(
    document: UploadFile,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> Document:
    db_document = await save_document(document, current_user, db)
    process_document.delay(db_document.id)

    return db_document


@v1_router.post("/documents/url", response_model=DocumentResponse)
async def post_document_from_url(
    data: DocumentFromUrl,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> Document:
    fetched = await fetch_url(str(data.url))
    db_document = await store_document(
        fetched.file,
        fetched.filename,
        fetched.content_type,
        fetched.size,
        current_user,
        db,
    )
    process_document.delay(db_document.id)

    return db_document


@v1_router.get("/documents", response_model=list[DocumentResponse])
async def get_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> list[Document]:
    result = await db.scalars(
        select(Document)
        .where(visible_to(current_user))
        .order_by(Document.created_at.desc())
    )
    return list(result)


@v1_router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> Document:
    return await get_visible_document(document_id, db, current_user)


@v1_router.patch("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    data: DocumentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_admin),
) -> Document:
    db_document = await get_own_document(document_id, db, current_user)

    db_document.is_shared = data.is_shared
    await db.commit()

    return db_document


@v1_router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> None:
    db_document = await get_own_document(document_id, db, current_user)

    if db_document.storage_key:
        await run_in_threadpool(s3_storage.delete, db_document.storage_key)

    await db.delete(db_document)
    await db.commit()
