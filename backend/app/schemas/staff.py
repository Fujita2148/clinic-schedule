import uuid

from pydantic import BaseModel


class StaffBase(BaseModel):
    name: str
    employment_type: str
    job_category: str
    can_drive: bool = False
    can_bicycle: bool = True
    work_hours_default: dict | None = None
    is_active: bool = True


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    name: str | None = None
    employment_type: str | None = None
    job_category: str | None = None
    can_drive: bool | None = None
    can_bicycle: bool | None = None
    work_hours_default: dict | None = None
    is_active: bool | None = None


class StaffResponse(StaffBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class SkillMasterResponse(BaseModel):
    code: str
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}
