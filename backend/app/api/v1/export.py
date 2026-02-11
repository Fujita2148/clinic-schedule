import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schedule import Schedule
from app.services.export_service import generate_csv, generate_excel, generate_pdf

router = APIRouter(prefix="/schedules/{schedule_id}/export", tags=["export"])


@router.get("/csv")
async def export_csv(schedule_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    csv_content = await generate_csv(db, schedule)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=schedule_{schedule.year_month}.csv"},
    )


@router.get("/excel")
async def export_excel(schedule_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    content = await generate_excel(db, schedule)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=schedule_{schedule.year_month}.xlsx"},
    )


@router.get("/pdf")
async def export_pdf(schedule_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    content = await generate_pdf(db, schedule)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=schedule_{schedule.year_month}.pdf"},
    )
