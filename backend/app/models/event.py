"""Event model — scheduling events/tasks to be assigned."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Event(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "events"

    type_code: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("task_types.code"), nullable=True
    )
    subject_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    subject_anonymous_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location_type: Mapped[str] = mapped_column(String(20), nullable=False)  # in_clinic | outing | visit
    duration_hours: Mapped[int] = mapped_column(Integer, default=1)
    time_constraint_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # fixed | range | candidates
    time_constraint_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list] = mapped_column(JSON, default=list)
    required_resources: Mapped[list] = mapped_column(JSON, default=list)
    assigned_staff_ids: Mapped[list] = mapped_column(JSON, default=list)
    priority: Mapped[str] = mapped_column(
        String(20), default="required"
    )  # required | high | medium | low
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="unassigned"
    )  # unassigned | assigned | hold | done
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    natural_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    links: Mapped[list] = mapped_column(JSON, default=list)
    provisional_constraints: Mapped[list] = mapped_column(JSON, default=list)
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("schedules.id"), nullable=True
    )
