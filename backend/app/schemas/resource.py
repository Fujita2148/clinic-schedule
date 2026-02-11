import uuid

from pydantic import BaseModel


class ResourceBase(BaseModel):
    type: str
    name: str
    capacity: int = 1
    priority_for: list[str] = []
    is_active: bool = True


class ResourceCreate(ResourceBase):
    pass


class ResourceResponse(ResourceBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}
