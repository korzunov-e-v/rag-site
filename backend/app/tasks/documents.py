from backend.app.celery_app import celery_app
from backend.app.db.connect import SessionLocal
from backend.app.db.models import Document
from backend.app.services.process_doc import process_doc

@celery_app.task
def process_document(document_id: int) -> None:
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return
        process_doc(document, db)
    finally:
        db.close()
