import uvicorn
from fastapi import FastAPI

from backend.app.api.v1 import v1_router
from backend.app.db.connect import create_db_and_tables

app = FastAPI()
app.include_router(v1_router, prefix="/api/v1")
create_db_and_tables()


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == '__main__':
    main()
