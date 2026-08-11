import socketio
import uvicorn
from fastapi import FastAPI

from backend.app.api.v1 import v1_router
from backend.app.socketio import sio


fastapi_app = FastAPI()

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
