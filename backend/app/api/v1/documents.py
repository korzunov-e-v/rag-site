from backend.app.api.v1.router import v1_router
from backend.app.api.v1.schemas import DocumentCreate
from backend.app.db.connect import Session
from backend.app.db.models.document import Document


@v1_router.post("/documents")
def post_document(document: DocumentCreate):
    db = Session()
    document = Document(**document.model_dump())
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
