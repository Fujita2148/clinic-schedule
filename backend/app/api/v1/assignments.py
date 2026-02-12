import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schedule import Schedule, ScheduleAssignment
from app.schemas.schedule import AssignmentCreate, AssignmentResponse, AssignmentUpdate

router = APIRouter(prefix="/schedules/{schedule_id}/assignments", tags=["assignments"])


@router.get("", response_model=list[AssignmentResponse])
async def list_assignments(
    schedule_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    staff_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    query = select(ScheduleAssignment).where(ScheduleAssignment.schedule_id == schedule_id)
    if date_from:
        query = query.where(ScheduleAssignment.date >= date_from)
    if date_to:
        query = query.where(ScheduleAssignment.date <= date_to)
    if staff_id:
        query = query.where(ScheduleAssignment.staff_id == staff_id)
    query = query.order_by(ScheduleAssignment.date, ScheduleAssignment.time_block)
    result = await db.execute(query)
    return result.scalars().all()


@router.put("", response_model=AssignmentResponse)
async def upsert_assignment(
    schedule_id: uuid.UUID,
    data: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.status == "confirmed":
        raise HTTPException(status_code=403, detail="確定済みスケジュールは編集できません")

    valid_blocks = {"am", "lunch", "pm", "15", "16", "17", "18plus"}
    if data.time_block not in valid_blocks:
        raise HTTPException(status_code=400, detail=f"Invalid time_block. Must be one of: {valid_blocks}")

    existing = await db.execute(
        select(ScheduleAssignment).where(
            and_(
                ScheduleAssignment.schedule_id == schedule_id,
                ScheduleAssignment.staff_id == data.staff_id,
                ScheduleAssignment.date == data.date,
                ScheduleAssignment.time_block == data.time_block,
            )
        )
    )
    assignment = existing.scalars().first()

    if assignment:
        if assignment.is_locked:
            raise HTTPException(status_code=409, detail="Assignment is locked")
        for key, value in data.model_dump().items():
            setattr(assignment, key, value)
    else:
        assignment = ScheduleAssignment(schedule_id=schedule_id, **data.model_dump())
        db.add(assignment)

    await db.flush()
    await db.refresh(assignment)
    return assignment


@router.patch("/{assignment_id}/lock", response_model=AssignmentResponse)
async def toggle_lock(
    schedule_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.get(Schedule, schedule_id)
    if schedule and schedule.status == "confirmed":
        raise HTTPException(status_code=403, detail="確定済みスケジュールは編集できません")
    assignment = await db.get(ScheduleAssignment, assignment_id)
    if not assignment or assignment.schedule_id != schedule_id:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assignment.is_locked = not assignment.is_locked
    await db.flush()
    await db.refresh(assignment)
    return assignment


@router.delete("/{assignment_id}", status_code=204)
async def delete_assignment(
    schedule_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.get(Schedule, schedule_id)
    if schedule and schedule.status == "confirmed":
        raise HTTPException(status_code=403, detail="確定済みスケジュールは編集できません")
    assignment = await db.get(ScheduleAssignment, assignment_id)
    if not assignment or assignment.schedule_id != schedule_id:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.is_locked:
        raise HTTPException(status_code=409, detail="Assignment is locked")
    await db.delete(assignment)
