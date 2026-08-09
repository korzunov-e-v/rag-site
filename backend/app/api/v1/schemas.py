from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(BaseModel):
    filename: str


class DocumentResponse(Model):
    id: int
    filename: str
