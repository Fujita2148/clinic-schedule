import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.day_program import DayProgram
from app.models.master import TimeBlockMaster
from app.models.schedule import Schedule, ScheduleAssignment
from app.models.staff import Staff
from app.schemas.schedule import GridCell, GridData, GridRow
from app.services.schedule_service import build_grid_data

router = APIRouter(prefix="/schedules/{schedule_id}/grid", tags=["grid"])


@router.get("", response_model=GridData)
async def get_grid(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return await build_grid_data(db, schedule)
