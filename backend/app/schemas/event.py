"""Pydantic schemas for Event CRUD."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class EventBase(BaseModel):
    type_code: str | None = None
    subject_name: str | None = None
    location_type: str = "in_clinic"
    duration_hours: int = 1
    time_constraint_type: str = "fixed"
    time_constraint_data: dict = Field(default_factory=dict)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_resources: list[str] = Field(default_factory=list)
    assigned_staff_ids: list[str] = Field(default_factory=list)
    priority: str = "required"
    deadline: date | None = None
    status: str = "unassigned"
    notes: str | None = None
    natural_text: str | None = None
    attributes: dict = Field(default_factory=dict)
    links: list = Field(default_factory=list)
    provisional_constraints: list = Field(default_factory=list)
    schedule_id: uuid.UUID | None = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    type_code: str | None = None
    subject_name: str | None = None
    location_type: str | None = None
    duration_hours: int | None = None
    time_constraint_type: str | None = None
    time_constraint_data: dict | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    required_resources: list[str] | None = None
    assigned_staff_ids: list[str] | None = None
    priority: str | None = None
    deadline: date | None = None
    status: str | None = None
    notes: str | None = None
    natural_text: str | None = None
    attributes: dict | None = None
    links: list | None = None
    provisional_constraints: list | None = None
    schedule_id: uuid.UUID | None = None


class EventResponse(EventBase):
    id: uuid.UUID
    subject_anonymous_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
