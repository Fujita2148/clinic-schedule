import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schedule import Schedule
from app.models.violation import Violation
from app.services.validation_service import validate_schedule

router = APIRouter(prefix="/schedules/{schedule_id}/violations", tags=["violations"])


@router.get("")
async def list_violations(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    result = await db.execute(
        select(Violation)
        .where(Violation.schedule_id == schedule_id)
        .order_by(Violation.affected_date, Violation.affected_time_block)
    )
    violations = result.scalars().all()
    return [
        {
            "id": str(v.id),
            "violation_type": v.violation_type,
            "severity": v.severity,
            "description": v.description,
            "affected_date": str(v.affected_date) if v.affected_date else None,
            "affected_time_block": v.affected_time_block,
            "affected_staff": v.affected_staff or [],
            "suggestion": v.suggestion,
            "is_resolved": v.is_resolved,
        }
        for v in violations
    ]


@router.post("/check")
async def check_violations(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Run validation checks
    found = await validate_schedule(db, schedule_id)

    # Clear old violations and insert new ones
    old_result = await db.execute(
        select(Violation).where(Violation.schedule_id == schedule_id)
    )
    for old in old_result.scalars().all():
        await db.delete(old)

    new_violations = []
    for v in found:
        violation = Violation(
            schedule_id=schedule_id,
            rule_id=v.get("rule_id"),
            violation_type=v["type"],
            severity=v.get("severity"),
            description=v["description"],
            affected_date=v.get("affected_date"),
            affected_time_block=v.get("affected_time_block"),
            affected_staff=v.get("affected_staff", []),
            suggestion=v.get("suggestion"),
        )
        db.add(violation)
        new_violations.append(violation)

    await db.flush()
    for nv in new_violations:
        await db.refresh(nv)

    return [
        {
            "id": str(v.id),
            "violation_type": v.violation_type,
            "severity": v.severity,
            "description": v.description,
            "affected_date": str(v.affected_date) if v.affected_date else None,
            "affected_time_block": v.affected_time_block,
            "affected_staff": v.affected_staff or [],
            "suggestion": v.suggestion,
            "is_resolved": v.is_resolved,
        }
        for v in new_violations
    ]
