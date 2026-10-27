import asyncio
import logging

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.celery_app import celery_app
from backend.app.db.connect import SessionLocal, engine
from backend.app.db.enums import DocumentStatus
from backend.app.db.models import Document
from backend.app.exceptions import RetryableError
from backend.app.services.process_doc import process_doc
from backend.app.services.summary import summarize_document
from backend.app.socketio_publisher import (
    emit_document_description,
    emit_document_status,
)

logger = logging.getLogger(__name__)


async def set_status(
    db: AsyncSession,
    document: Document,
    status: DocumentStatus,
    error_message: str | None = None,
) -> None:
    document.status = status
    document.error_message = error_message
    await db.commit()

    emit_document_status(document.id, status.value, document.owner_id)


async def document_exists(db: AsyncSession, document_id: int) -> bool:
    return await db.scalar(
        select(Document.id).where(Document.id == document_id)
    ) is not None


async def run_process_document(
    task: Task,
    document_id: int,
) -> None:
    async with SessionLocal() as db:
        document = await db.get(Document, document_id)

        if document is None:
            return

        await set_status(db, document, DocumentStatus.PROCESSING)

        try:
            await process_doc(document, db)
            await set_status(db, document, DocumentStatus.PROCESSED)
            summarize.delay(document_id)

        except RetryableError as error:
            await db.rollback()

            if task.request.retries >= task.max_retries:
                await set_status(db, document, DocumentStatus.FAILED, str(error))
                raise

            # Документ остаётся в обработке: пользователь не увидит
            # ошибку, пока ретраи не закончатся.
            document.error_message = str(error)
            await db.commit()

            raise task.retry(
                exc=error,
                countdown=2 ** task.request.retries * 10,
            )

        except Exception as error:
            await db.rollback()

            if not await document_exists(db, document_id):
                # Пользователь удалил документ, пока тот обрабатывался.
                logger.info("Document %s was deleted during processing", document_id)
                return

            await set_status(db, document, DocumentStatus.FAILED, str(error))
            raise


async def run_in_new_loop(coroutine) -> None:
    try:
        await coroutine
    finally:
        # asyncio.run создаёт новый event loop на каждую задачу, а соединения
        # из пула привязаны к старому — закрываем их.
        await engine.dispose()


async def run_summarize(document_id: int) -> None:
    async with SessionLocal() as db:
        document = await db.get(Document, document_id)

        if document is None:
            return

        try:
            description = await summarize_document(document, db)
        except Exception:
            # Описание — приятное дополнение, документ без него полностью рабочий.
            logger.exception("Failed to summarize document %s", document_id)
            return

        if description is None or not await document_exists(db, document_id):
            return

        document.description = description
        await db.commit()

        emit_document_description(document_id, description, document.owner_id)


@celery_app.task
def summarize(document_id: int) -> None:
    asyncio.run(run_in_new_loop(run_summarize(document_id)))


@celery_app.task(
    bind=True,
    max_retries=3,
)
def process_document(
    self: Task,
    document_id: int,
) -> None:
    asyncio.run(run_in_new_loop(run_process_document(self, document_id)))
