from contextlib import asynccontextmanager

import socketio
import uvicorn
from fastapi import FastAPI

from backend.app.api.v1 import v1_router
from backend.app.services.storage import s3_storage
from backend.app.socketio import sio


@asynccontextmanager
async def lifespan(app: FastAPI):
    s3_storage.ensure_bucket()
    yield


fastapi_app = FastAPI(lifespan=lifespan)

fastapi_app.include_router(
    v1_router,
    prefix="/api/v1",
)

app = socketio.ASGIApp(
    sio,
    other_asgi_app=fastapi_app,
)


def main():
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    main()
