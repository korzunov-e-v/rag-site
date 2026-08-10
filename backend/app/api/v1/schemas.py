from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(BaseModel):
    filename: str


class DocumentResponsePre(Model):
    id: int
    filename: str
    status: str


class DocumentResponse(Model):
    id: int
    filename: str
    content_type: str
    size: int
    status: str
    created_at: datetime
    description: str | None
