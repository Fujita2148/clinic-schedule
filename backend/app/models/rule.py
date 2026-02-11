"""Rule model — scheduling constraints/rules."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Rule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "rules"

    natural_text: Mapped[str] = mapped_column(Text, nullable=False)
    template_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # recurring | specific_date | headcount | skill_req | resource_req | preference | availability
    scope: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    hard_or_soft: Mapped[str] = mapped_column(String(10), nullable=False)  # hard | soft
    weight: Mapped[int] = mapped_column(Integer, default=100)  # 1-1000 for soft constraints
    body: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    exceptions: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    applies_to: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
