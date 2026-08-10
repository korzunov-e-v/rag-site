from celery import Task

from backend.app.celery_app import celery_app
from backend.app.db.connect import SessionLocal
from backend.app.db.enums import DocumentStatus
from backend.app.db.models import Document
from backend.app.exceptions import RetryableError
from backend.app.services.process_doc import process_doc


@celery_app.task(bind=True, max_retries=3)
def process_document(self: Task, document_id: int) -> None:
    with SessionLocal() as db:
        document = db.get(Document, document_id)

        if document is None:
            return

        try:
            process_doc(document, db)

        except RetryableError as error:
            if self.request.retries >= self.max_retries:
                document.status = DocumentStatus.FAILED
                db.commit()
                raise

            raise self.retry(
                exc=error,
                countdown=2 ** self.request.retries * 10,
            )

        except Exception:
            document.status = DocumentStatus.FAILED
            db.commit()
            raise
