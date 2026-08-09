from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.base import Base

engine = create_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/rag")
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
