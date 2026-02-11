import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Staff(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "staffs"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # full_time | part_time
    job_category: Mapped[str] = mapped_column(String(50), nullable=False)  # 医師 | 事務 | PSW | CP | 看護師
    can_drive: Mapped[bool] = mapped_column(Boolean, default=False)
    can_bicycle: Mapped[bool] = mapped_column(Boolean, default=True)
    work_hours_default: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    skills: Mapped[list["StaffSkill"]] = relationship(back_populates="staff", cascade="all, delete-orphan")
    assignments: Mapped[list["ScheduleAssignment"]] = relationship(back_populates="staff")  # noqa: F821


class SkillMaster(Base):
    __tablename__ = "skill_master"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class StaffSkill(Base):
    __tablename__ = "staff_skills"

    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staffs.id"), primary_key=True)
    skill_code: Mapped[str] = mapped_column(ForeignKey("skill_master.code"), primary_key=True)
    level: Mapped[str] = mapped_column(String(20), default="qualified")  # qualified | preferred | learning

    staff: Mapped["Staff"] = relationship(back_populates="skills")
