import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Schedule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "schedules"

    year_month: Mapped[str] = mapped_column(String(7), nullable=False, unique=True)  # '2025-05'
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | reviewing | confirmed
    solver_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    assignments: Mapped[list["ScheduleAssignment"]] = relationship(back_populates="schedule", cascade="all, delete-orphan")
    day_programs: Mapped[list["DayProgram"]] = relationship(back_populates="schedule", cascade="all, delete-orphan")  # noqa: F821


class ScheduleAssignment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "schedule_assignments"
    __table_args__ = (
        UniqueConstraint("schedule_id", "staff_id", "date", "time_block", name="uq_assignment"),
    )

    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.id"), nullable=False)
    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staffs.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time_block: Mapped[str] = mapped_column(String(10), nullable=False)  # am|lunch|pm|15|16|17|18plus
    task_type_code: Mapped[str | None] = mapped_column(ForeignKey("task_types.code"), nullable=True)
    display_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_color: Mapped[str | None] = mapped_column(String(20), nullable=True)  # off|pre_work|post_work|visit|custom
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual | solver | imported

    schedule: Mapped["Schedule"] = relationship(back_populates="assignments")
    staff: Mapped["Staff"] = relationship(back_populates="assignments")  # noqa: F821
