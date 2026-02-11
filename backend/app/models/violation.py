import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class Violation(UUIDMixin, Base):
    __tablename__ = "violations"

    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.id"), nullable=False)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    violation_type: Mapped[str] = mapped_column(String(20), nullable=False)  # hard | soft
    severity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    affected_time_block: Mapped[str | None] = mapped_column(String(10), nullable=True)
    affected_staff: Mapped[list] = mapped_column(JSON, default=list)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
