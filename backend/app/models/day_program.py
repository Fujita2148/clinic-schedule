import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class DayProgram(UUIDMixin, Base):
    __tablename__ = "day_programs"
    __table_args__ = (
        UniqueConstraint("schedule_id", "date", "time_block", name="uq_day_program"),
    )

    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time_block: Mapped[str] = mapped_column(String(10), nullable=False)
    program_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_nightcare: Mapped[bool] = mapped_column(Boolean, default=False)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    schedule: Mapped["Schedule"] = relationship(back_populates="day_programs")  # noqa: F821
