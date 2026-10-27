import logging

import socketio

from backend.app.settings import settings

logger = logging.getLogger(__name__)

manager = socketio.RedisManager(settings.redis_url)


def user_room(user_id: int) -> str:
    return f"user:{user_id}"


def emit_document_status(
    document_id: int,
    status: str,
    owner_id: int,
) -> None:
    logger.info(
        "Document status: id=%s status=%s owner=%s",
        document_id,
        status,
        owner_id,
    )
    manager.emit(
        "document:status",
        {
            "document_id": document_id,
            "status": status,
        },
        room=user_room(owner_id),
    )
