from celery import Celery

from backend.app.settings import settings


celery_app = Celery(
    "rag",
    broker=settings.rabbitmq_url,
    include=["backend.app.tasks.documents"],
)
