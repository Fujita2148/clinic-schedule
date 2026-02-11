import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class Resource(UUIDMixin, Base):
    __tablename__ = "resources"

    type: Mapped[str] = mapped_column(String(50), nullable=False)  # car | bicycle | room
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    priority_for: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ResourceBooking(UUIDMixin, Base):
    __tablename__ = "resource_bookings"
    __table_args__ = (
        UniqueConstraint("resource_id", "date", "time_block", "assignment_id", name="uq_resource_booking"),
    )

    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id"), nullable=False)
    assignment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedule_assignments.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time_block: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
