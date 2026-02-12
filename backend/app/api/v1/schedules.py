import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.schedule import Schedule, ScheduleAssignment
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleStatusUpdate

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Schedule).order_by(Schedule.year_month.desc()))
    return result.scalars().all()


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Schedule).where(Schedule.year_month == data.year_month))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="Schedule for this month already exists")
    schedule = Schedule(year_month=data.year_month)
    db.add(schedule)
    await db.flush()
    await db.refresh(schedule)
    return schedule


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.patch("/{schedule_id}/status", response_model=ScheduleResponse)
async def update_schedule_status(
    schedule_id: uuid.UUID,
    data: ScheduleStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    valid_transitions = {
        "draft": ["reviewing"],
        "reviewing": ["confirmed", "draft"],
        "confirmed": [],
    }
    allowed = valid_transitions.get(schedule.status, [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{schedule.status}' to '{data.status}'. Allowed: {allowed}",
        )
    schedule.status = data.status
    await db.flush()
    await db.refresh(schedule)
    return schedule
