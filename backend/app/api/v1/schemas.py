from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(BaseModel):
    filename: str


class DocumentFromUrl(BaseModel):
    url: HttpUrl


class DocumentResponsePre(Model):
    id: int
    filename: str
    status: str


class DocumentResponse(Model):
    id: int
    owner_id: int
    filename: str
    content_type: str | None
    size: int
    status: str
    created_at: datetime
    description: str | None
    is_shared: bool


class DocumentUpdate(BaseModel):
    is_shared: bool
