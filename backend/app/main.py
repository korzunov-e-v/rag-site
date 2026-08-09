import uvicorn
from fastapi import FastAPI

from backend.app.api.v1 import v1_router

app = FastAPI()
app.include_router(v1_router, prefix="/api/v1")


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == '__main__':
    main()
