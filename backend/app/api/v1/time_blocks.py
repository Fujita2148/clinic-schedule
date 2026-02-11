from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.master import TimeBlockMaster
from app.schemas.master import TimeBlockResponse

router = APIRouter(prefix="/time-blocks", tags=["time_blocks"])


@router.get("", response_model=list[TimeBlockResponse])
async def list_time_blocks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TimeBlockMaster).order_by(TimeBlockMaster.sort_order))
    rows = result.scalars().all()
    return [
        TimeBlockResponse(
            code=r.code,
            display_name=r.display_name,
            start_time=r.start_time.strftime("%H:%M"),
            end_time=r.end_time.strftime("%H:%M"),
            duration_minutes=r.duration_minutes,
            sort_order=r.sort_order,
        )
        for r in rows
    ]
