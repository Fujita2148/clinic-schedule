"""Validation service — constraint checking for schedule assignments."""

from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource import ResourceBooking
from app.models.schedule import ScheduleAssignment


async def check_duplicate_assignment(
    db: AsyncSession,
    schedule_id,
    staff_id,
    target_date: date,
    time_block: str,
    exclude_id=None,
) -> str | None:
    """Check if a staff member already has an assignment at this slot."""
    query = select(ScheduleAssignment).where(
        and_(
            ScheduleAssignment.schedule_id == schedule_id,
            ScheduleAssignment.staff_id == staff_id,
            ScheduleAssignment.date == target_date,
            ScheduleAssignment.time_block == time_block,
        )
    )
    if exclude_id:
        query = query.where(ScheduleAssignment.id != exclude_id)
    result = await db.execute(query)
    existing = result.scalars().first()
    if existing:
        return f"職員は既に {target_date} {time_block} に割当があります"
    return None


async def check_resource_capacity(
    db: AsyncSession,
    resource_id,
    target_date: date,
    time_block: str,
    capacity: int,
    exclude_booking_id=None,
) -> str | None:
    """Check if resource capacity would be exceeded."""
    query = select(func.count(ResourceBooking.id)).where(
        and_(
            ResourceBooking.resource_id == resource_id,
            ResourceBooking.date == target_date,
            ResourceBooking.time_block == time_block,
        )
    )
    if exclude_booking_id:
        query = query.where(ResourceBooking.id != exclude_booking_id)
    result = await db.execute(query)
    count = result.scalar() or 0
    if count >= capacity:
        return f"リソースの容量超過: {target_date} {time_block} (現在 {count}/{capacity})"
    return None


async def validate_schedule(db: AsyncSession, schedule_id) -> list[dict]:
    """Run all validation checks on a schedule. Returns list of violations."""
    violations = []

    # Check for duplicate assignments (same staff, same slot)
    result = await db.execute(
        select(
            ScheduleAssignment.staff_id,
            ScheduleAssignment.date,
            ScheduleAssignment.time_block,
            func.count(ScheduleAssignment.id).label("cnt"),
        )
        .where(ScheduleAssignment.schedule_id == schedule_id)
        .group_by(
            ScheduleAssignment.staff_id,
            ScheduleAssignment.date,
            ScheduleAssignment.time_block,
        )
        .having(func.count(ScheduleAssignment.id) > 1)
    )
    for row in result.all():
        violations.append({
            "type": "hard",
            "description": f"重複割当: staff={row.staff_id} date={row.date} block={row.time_block}",
            "affected_date": str(row.date),
            "affected_time_block": row.time_block,
            "affected_staff": [str(row.staff_id)],
        })

    return violations
