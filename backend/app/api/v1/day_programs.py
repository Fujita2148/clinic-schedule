import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.day_program import DayProgram
from app.models.schedule import Schedule
from app.schemas.day_program import DayProgramCreate, DayProgramResponse, DayProgramUpdate

router = APIRouter(prefix="/schedules/{schedule_id}/day-programs", tags=["day_programs"])


@router.get("", response_model=list[DayProgramResponse])
async def list_day_programs(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    result = await db.execute(
        select(DayProgram)
        .where(DayProgram.schedule_id == schedule_id)
        .order_by(DayProgram.date, DayProgram.time_block)
    )
    return result.scalars().all()


@router.put("/{target_date}", response_model=list[DayProgramResponse])
async def upsert_day_programs(
    schedule_id: uuid.UUID,
    target_date: date,
    data: list[DayProgramCreate],
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    results = []
    for item in data:
        existing = await db.execute(
            select(DayProgram).where(
                and_(
                    DayProgram.schedule_id == schedule_id,
                    DayProgram.date == target_date,
                    DayProgram.time_block == item.time_block,
                )
            )
        )
        program = existing.scalars().first()
        if program:
            for key, value in item.model_dump().items():
                setattr(program, key, value)
        else:
            program = DayProgram(schedule_id=schedule_id, **item.model_dump())
            db.add(program)
        await db.flush()
        await db.refresh(program)
        results.append(program)

    return results
