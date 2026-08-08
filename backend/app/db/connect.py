from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base

engine = create_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/rag")
Session = sessionmaker(bind=engine)

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
