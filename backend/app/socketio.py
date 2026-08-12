import socketio
import jwt

from backend.app.db.models import User
from backend.app.db.connect import SessionLocal
from backend.app.settings import settings
from backend.app.services.ask import ask_documents

connected_users: dict[str, int] = {}

manager = socketio.AsyncRedisManager(
    settings.redis_url
)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    client_manager=manager,
)


async def emit_document_status(
    document_id: int,
    status: str,
) -> None:
    print(
        f"SOCKET.IO EMIT: "
        f"document:status "
        f"id={document_id} "
        f"status={status}"
    )

    await sio.emit(
        "document:status",
        {
            "document_id": document_id,
            "status": status,
        },
    )


@sio.event
async def ask(sid, data):
    user_id = connected_users.get(sid)

    if user_id is None:
        await sio.emit(
            "ask:error",
            {
                "message": "Необходима авторизация",
            },
            to=sid,
        )
        return

    query = data["query"]

    print(
        f"SOCKET.IO ASK: "
        f"sid={sid} "
        f"query={query!r}"
    )

    await sio.emit(
        "ask:started",
        {},
        to=sid,
    )

    db = SessionLocal()

    try:
        async for result in ask_documents(query, db, user_id):

            if "error" in result:
                print(
                    f"DOCUMENT ERROR: "
                    f"id={result['document_id']} "
                    f"filename={result['filename']} "
                    f"error={result['error']}"
                )

                await sio.emit(
                    "document:error",
                    {
                        "document_id": result["document_id"],
                        "filename": result["filename"],
                        "message": "Не удалось обработать документ",
                    },
                    to=sid,
                )

                continue

            print(
                f"SOCKET.IO ANSWER: "
                f"document_id={result['document_id']} "
                f"filename={result['filename']}"
            )

            await sio.emit(
                "answer",
                result,
                to=sid,
            )

        print("SOCKET.IO EMIT: ask:finished")

        await sio.emit(
            "ask:finished",
            {},
            to=sid,
        )

    except Exception as exc:
        print(f"ASK ERROR: {exc}")

        await sio.emit(
            "ask:error",
            {
                "message": "Не удалось выполнить поиск",
            },
            to=sid,
        )

    finally:
        db.close()


@sio.event
async def connect(sid, environ, auth):
    if not auth:
        return False

    token = auth.get("token")

    if not token:
        return False

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id = int(payload["sub"])

    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return False

    db = SessionLocal()

    try:
        user = db.get(User, user_id)

        if user is None:
            return False

        connected_users[sid] = user.id

        print(
            f"SOCKET.IO AUTH: "
            f"sid={sid} "
            f"user_id={user.id}"
        )

    finally:
        db.close()

@sio.event
async def disconnect(sid):
    connected_users.pop(sid, None)
