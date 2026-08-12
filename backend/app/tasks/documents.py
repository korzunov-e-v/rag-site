import asyncio

from celery import Task

from backend.app.celery_app import celery_app
from backend.app.db.connect import SessionLocal
from backend.app.db.enums import DocumentStatus
from backend.app.db.models import Document
from backend.app.exceptions import RetryableError
from backend.app.services.process_doc import process_doc


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

        document.status = DocumentStatus.PROCESSING
        document.error_message = None
        db.commit()

        try:
            asyncio.run(process_doc(document, db))

            document.status = DocumentStatus.PROCESSED
            document.error_message = None
            db.commit()

        except RetryableError as error:
            db.rollback()

            document = db.get(Document, document_id)
            document.status = DocumentStatus.PROCESSING
            document.error_message = str(error)
            db.commit()

            if self.request.retries >= self.max_retries:
                document.status = DocumentStatus.FAILED
                db.commit()
                raise

            raise self.retry(
                exc=error,
                countdown=2 ** self.request.retries * 10,
            )

        except Exception as error:
            db.rollback()

            document = db.get(Document, document_id)
            document.status = DocumentStatus.FAILED
            document.error_message = str(error)
            db.commit()

            raise
