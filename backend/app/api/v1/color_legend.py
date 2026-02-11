from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.master import ColorLegend
from app.schemas.master import ColorLegendResponse, ColorLegendUpdate

router = APIRouter(prefix="/color-legend", tags=["color_legend"])


@router.get("", response_model=list[ColorLegendResponse])
async def list_color_legend(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ColorLegend).order_by(ColorLegend.sort_order))
    return result.scalars().all()


@router.put("/{code}", response_model=ColorLegendResponse)
async def update_color_legend(
    code: str, data: ColorLegendUpdate, db: AsyncSession = Depends(get_db)
):
    legend = await db.get(ColorLegend, code)
    if not legend:
        raise HTTPException(status_code=404, detail="Color legend not found")
    if legend.is_system:
        allowed = {"display_name", "bg_color", "text_color", "hatch_pattern", "icon"}
        update_data = data.model_dump(exclude_unset=True)
        for key in list(update_data.keys()):
            if key not in allowed:
                raise HTTPException(status_code=400, detail=f"Cannot modify '{key}' on system colors")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(legend, key, value)
    await db.flush()
    await db.refresh(legend)
    return legend
