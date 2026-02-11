import uuid
from datetime import date

from pydantic import BaseModel


class DayProgramBase(BaseModel):
    date: date
    time_block: str
    program_title: str | None = None
    is_nightcare: bool = False
    summary_text: str | None = None


class DayProgramCreate(DayProgramBase):
    pass


class DayProgramUpdate(BaseModel):
    program_title: str | None = None
    is_nightcare: bool | None = None
    summary_text: str | None = None


class DayProgramResponse(DayProgramBase):
    id: uuid.UUID
    schedule_id: uuid.UUID

    model_config = {"from_attributes": True}
