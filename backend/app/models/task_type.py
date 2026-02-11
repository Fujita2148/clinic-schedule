from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TaskType(Base):
    __tablename__ = "task_types"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    default_blocks: Mapped[list] = mapped_column(JSON, default=lambda: ["am"])
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list] = mapped_column(JSON, default=list)
    required_resources: Mapped[list] = mapped_column(JSON, default=list)
    min_staff: Mapped[int] = mapped_column(Integer, default=1)
    max_staff: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    location_type: Mapped[str] = mapped_column(String(20), default="in_clinic")
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
