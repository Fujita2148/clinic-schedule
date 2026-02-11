from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.task_type import TaskType
from app.schemas.task_type import TaskTypeCreate, TaskTypeResponse, TaskTypeUpdate

router = APIRouter(prefix="/task-types", tags=["task_types"])


@router.get("", response_model=list[TaskTypeResponse])
async def list_task_types(
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(TaskType)
    if is_active is not None:
        query = query.where(TaskType.is_active == is_active)
    query = query.order_by(TaskType.code)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=TaskTypeResponse, status_code=201)
async def create_task_type(data: TaskTypeCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.get(TaskType, data.code)
    if existing:
        raise HTTPException(status_code=409, detail="Task type code already exists")
    task_type = TaskType(**data.model_dump())
    db.add(task_type)
    await db.flush()
    await db.refresh(task_type)
    return task_type


@router.put("/{code}", response_model=TaskTypeResponse)
async def update_task_type(code: str, data: TaskTypeUpdate, db: AsyncSession = Depends(get_db)):
    task_type = await db.get(TaskType, code)
    if not task_type:
        raise HTTPException(status_code=404, detail="Task type not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(task_type, key, value)
    await db.flush()
    await db.refresh(task_type)
    return task_type


@router.delete("/{code}", status_code=204)
async def soft_delete_task_type(code: str, db: AsyncSession = Depends(get_db)):
    task_type = await db.get(TaskType, code)
    if not task_type:
        raise HTTPException(status_code=404, detail="Task type not found")
    task_type.is_active = False
    await db.flush()
