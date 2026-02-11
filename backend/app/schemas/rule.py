"""Pydantic schemas for Rule CRUD."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


TEMPLATE_TYPES = [
    "recurring",
    "specific_date",
    "headcount",
    "skill_req",
    "resource_req",
    "preference",
    "availability",
]


class RuleBase(BaseModel):
    natural_text: str
    template_type: str
    scope: dict = Field(default_factory=dict)
    hard_or_soft: str = "soft"  # hard | soft
    weight: int = 100  # 1-1000
    body: dict = Field(default_factory=dict)
    exceptions: list = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    applies_to: dict = Field(default_factory=dict)
    is_active: bool = True


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    natural_text: str | None = None
    template_type: str | None = None
    scope: dict | None = None
    hard_or_soft: str | None = None
    weight: int | None = None
    body: dict | None = None
    exceptions: list | None = None
    tags: list[str] | None = None
    applies_to: dict | None = None
    is_active: bool | None = None


class RuleResponse(RuleBase):
    id: uuid.UUID
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
