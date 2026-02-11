import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.staff import SkillMaster, Staff
from app.schemas.staff import SkillMasterResponse, StaffCreate, StaffResponse, StaffUpdate

router = APIRouter(prefix="/staffs", tags=["staffs"])


@router.get("", response_model=list[StaffResponse])
async def list_staffs(
    is_active: bool | None = None,
    job_category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Staff)
    if is_active is not None:
        query = query.where(Staff.is_active == is_active)
    if job_category:
        query = query.where(Staff.job_category == job_category)
    query = query.order_by(Staff.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=StaffResponse, status_code=201)
async def create_staff(data: StaffCreate, db: AsyncSession = Depends(get_db)):
    staff = Staff(**data.model_dump())
    db.add(staff)
    await db.flush()
    await db.refresh(staff)
    return staff


@router.get("/skills", response_model=list[SkillMasterResponse])
async def list_skills(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SkillMaster))
    return result.scalars().all()


@router.get("/{staff_id}", response_model=StaffResponse)
async def get_staff(staff_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    staff = await db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff


@router.put("/{staff_id}", response_model=StaffResponse)
async def update_staff(staff_id: uuid.UUID, data: StaffUpdate, db: AsyncSession = Depends(get_db)):
    staff = await db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(staff, key, value)
    await db.flush()
    await db.refresh(staff)
    return staff
