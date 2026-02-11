import uuid
from datetime import date

from pydantic import BaseModel


class ScheduleBase(BaseModel):
    year_month: str
    status: str = "draft"


class ScheduleCreate(BaseModel):
    year_month: str


class ScheduleResponse(ScheduleBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class AssignmentBase(BaseModel):
    staff_id: uuid.UUID
    date: date
    time_block: str
    task_type_code: str | None = None
    display_text: str | None = None
    status_color: str | None = None
    is_locked: bool = False
    source: str = "manual"


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    task_type_code: str | None = None
    display_text: str | None = None
    status_color: str | None = None
    is_locked: bool | None = None


class AssignmentResponse(AssignmentBase):
    id: uuid.UUID
    schedule_id: uuid.UUID

    model_config = {"from_attributes": True}


class GridCell(BaseModel):
    assignment_id: uuid.UUID | None = None
    task_type_code: str | None = None
    display_text: str | None = None
    status_color: str | None = None
    is_locked: bool = False
    source: str = "manual"


class GridRow(BaseModel):
    date: date
    time_block: str
    time_block_display: str
    program_title: str | None = None
    is_nightcare: bool = False
    summary_text: str | None = None
    cells: dict[str, GridCell]  # staff_id -> cell data


class GridData(BaseModel):
    schedule_id: uuid.UUID
    year_month: str
    staff_list: list[dict]  # [{id, name, job_category}]
    rows: list[GridRow]
