import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.staff import SkillMaster, Staff, StaffSkill
from app.schemas.staff import (
    SkillMasterResponse,
    StaffCreate,
    StaffResponse,
    StaffSkillCreate,
    StaffSkillResponse,
    StaffUpdate,
)

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


@router.delete("/{staff_id}", status_code=204)
async def soft_delete_staff(staff_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    staff = await db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    staff.is_active = False
    await db.flush()


@router.get("/{staff_id}/skills", response_model=list[StaffSkillResponse])
async def list_staff_skills(staff_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    staff = await db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    result = await db.execute(select(StaffSkill).where(StaffSkill.staff_id == staff_id))
    return result.scalars().all()


@router.put("/{staff_id}/skills", response_model=list[StaffSkillResponse])
async def replace_staff_skills(
    staff_id: uuid.UUID,
    data: list[StaffSkillCreate],
    db: AsyncSession = Depends(get_db),
):
    staff = await db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    existing = await db.execute(select(StaffSkill).where(StaffSkill.staff_id == staff_id))
    for sk in existing.scalars().all():
        await db.delete(sk)
    await db.flush()
    results = []
    for item in data:
        skill = StaffSkill(staff_id=staff_id, skill_code=item.skill_code, level=item.level)
        db.add(skill)
        await db.flush()
        await db.refresh(skill)
        results.append(skill)
    return results
