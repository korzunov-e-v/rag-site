import asyncio

from celery import Task
from sqlalchemy.orm import Session

from backend.app.celery_app import celery_app
from backend.app.db.connect import SessionLocal
from backend.app.db.enums import DocumentStatus
from backend.app.db.models import Document
from backend.app.exceptions import RetryableError
from backend.app.services.process_doc import process_doc
from backend.app.socketio_publisher import emit_document_status


def set_status(
    db: Session,
    document: Document,
    status: DocumentStatus,
    error_message: str | None = None,
) -> None:
    document.status = status
    document.error_message = error_message
    db.commit()

    emit_document_status(document.id, status.value)


@celery_app.task(
    bind=True,
    max_retries=3,
)
def process_document(
    self: Task,
    document_id: int,
) -> None:
    with SessionLocal() as db:
        document = db.get(Document, document_id)

        if document is None:
            return

        set_status(db, document, DocumentStatus.PROCESSING)

        try:
            asyncio.run(process_doc(document, db))
            set_status(db, document, DocumentStatus.PROCESSED)

        except RetryableError as error:
            db.rollback()

            if self.request.retries >= self.max_retries:
                set_status(db, document, DocumentStatus.FAILED, str(error))
                raise

            # Документ остаётся в обработке: пользователь не увидит
            # ошибку, пока ретраи не закончатся.
            document.error_message = str(error)
            db.commit()

            raise self.retry(
                exc=error,
                countdown=2 ** self.request.retries * 10,
            )

        except Exception as error:
            db.rollback()
            set_status(db, document, DocumentStatus.FAILED, str(error))
            raise
