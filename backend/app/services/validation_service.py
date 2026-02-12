"""Validation service — comprehensive constraint checking for schedule assignments."""

from collections import defaultdict
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.resource import Resource, ResourceBooking
from app.models.rule import Rule
from app.models.schedule import ScheduleAssignment
from app.models.staff import Staff, StaffSkill
from app.models.task_type import TaskType

WEEKDAY_LABELS = ["月", "火", "水", "木", "金", "土", "日"]


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


async def _check_duplicates(db: AsyncSession, schedule_id) -> list[dict]:
    """Check for duplicate assignments (same staff, same slot)."""
    violations = []
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
            "description": f"重複割当: {row.date} {row.time_block}",
            "affected_date": str(row.date),
            "affected_time_block": row.time_block,
            "affected_staff": [str(row.staff_id)],
            "severity": 1000,
            "suggestion": "同じ時間帯に複数の割当があります。1つを削除してください。",
        })
    return violations


async def _check_skill_requirements(db: AsyncSession, schedule_id) -> list[dict]:
    """Check that assigned staff have required skills for their tasks."""
    violations = []

    # Get all assignments with task types that have required skills
    result = await db.execute(
        select(ScheduleAssignment, TaskType)
        .join(TaskType, ScheduleAssignment.task_type_code == TaskType.code)
        .where(ScheduleAssignment.schedule_id == schedule_id)
    )
    assignments_with_tasks = result.all()

    if not assignments_with_tasks:
        return violations

    # Filter to only those with required skills
    assignments_needing_skills = [
        (a, tt) for a, tt in assignments_with_tasks if tt.required_skills
    ]
    if not assignments_needing_skills:
        return violations

    # Collect all staff IDs and fetch their skills in bulk
    staff_ids = {a.staff_id for a, _ in assignments_needing_skills}
    skill_result = await db.execute(
        select(StaffSkill).where(StaffSkill.staff_id.in_(staff_ids))
    )
    staff_skills_map: dict[str, set[str]] = defaultdict(set)
    for ss in skill_result.scalars().all():
        staff_skills_map[str(ss.staff_id)].add(ss.skill_code)

    # Fetch staff names
    staff_result = await db.execute(select(Staff).where(Staff.id.in_(staff_ids)))
    staff_names = {str(s.id): s.name for s in staff_result.scalars().all()}

    for assignment, task_type in assignments_needing_skills:
        required = task_type.required_skills or []
        staff_id_str = str(assignment.staff_id)
        staff_skill_codes = staff_skills_map.get(staff_id_str, set())
        missing = [s for s in required if s not in staff_skill_codes]
        if missing:
            staff_name = staff_names.get(staff_id_str, "不明")
            violations.append({
                "type": "hard",
                "description": (
                    f"スキル不足: {staff_name}に{task_type.display_name}の"
                    f"必須スキル({', '.join(missing)})がありません"
                ),
                "affected_date": str(assignment.date),
                "affected_time_block": assignment.time_block,
                "affected_staff": [staff_id_str],
                "severity": 900,
                "suggestion": f"必須スキル{', '.join(missing)}を持つ職員に変更してください。",
            })
    return violations


async def _check_min_staff(db: AsyncSession, schedule_id) -> list[dict]:
    """Check minimum staff requirements for task types (e.g., daycare needs 2+)."""
    violations = []

    # Get task types with min_staff > 1
    tt_result = await db.execute(
        select(TaskType).where(TaskType.min_staff > 1, TaskType.is_active == True)  # noqa: E712
    )
    task_types = {t.code: t for t in tt_result.scalars().all()}
    if not task_types:
        return violations

    # Count staff per (date, time_block, task_type_code)
    result = await db.execute(
        select(
            ScheduleAssignment.date,
            ScheduleAssignment.time_block,
            ScheduleAssignment.task_type_code,
            func.count(ScheduleAssignment.id).label("cnt"),
        )
        .where(
            ScheduleAssignment.schedule_id == schedule_id,
            ScheduleAssignment.task_type_code.in_(list(task_types.keys())),
        )
        .group_by(
            ScheduleAssignment.date,
            ScheduleAssignment.time_block,
            ScheduleAssignment.task_type_code,
        )
    )
    for row in result.all():
        tt = task_types.get(row.task_type_code)
        if tt and row.cnt < tt.min_staff:
            violations.append({
                "type": "soft",
                "description": (
                    f"人員不足: {row.date} {row.time_block} の{tt.display_name}に"
                    f"最低{tt.min_staff}名必要ですが{row.cnt}名しかいません"
                ),
                "affected_date": str(row.date),
                "affected_time_block": row.time_block,
                "affected_staff": [],
                "severity": 700,
                "suggestion": f"あと{tt.min_staff - row.cnt}名追加してください。",
            })
    return violations


async def _check_visit_transport(db: AsyncSession, schedule_id) -> list[dict]:
    """Check that staff assigned to visit tasks can use required transport."""
    violations = []

    result = await db.execute(
        select(ScheduleAssignment, TaskType, Staff)
        .join(TaskType, ScheduleAssignment.task_type_code == TaskType.code)
        .join(Staff, ScheduleAssignment.staff_id == Staff.id)
        .where(
            ScheduleAssignment.schedule_id == schedule_id,
            TaskType.location_type == "visit",
        )
    )
    for assignment, task_type, staff in result.all():
        required_resources = task_type.required_resources or []
        if "car" in required_resources and not staff.can_drive:
            violations.append({
                "type": "hard",
                "description": (
                    f"運転不可: {staff.name}は運転ができませんが"
                    f"車が必要な{task_type.display_name}に割り当てられています"
                ),
                "affected_date": str(assignment.date),
                "affected_time_block": assignment.time_block,
                "affected_staff": [str(staff.id)],
                "severity": 800,
                "suggestion": "運転可能な職員に変更してください。",
            })
        if "bicycle" in required_resources and not staff.can_bicycle:
            violations.append({
                "type": "soft",
                "description": (
                    f"自転車不可: {staff.name}は自転車が使えませんが"
                    f"{task_type.display_name}に割り当てられています"
                ),
                "affected_date": str(assignment.date),
                "affected_time_block": assignment.time_block,
                "affected_staff": [str(staff.id)],
                "severity": 500,
                "suggestion": "自転車を使用できる職員に変更してください。",
            })
    return violations


async def _check_consecutive_work(db: AsyncSession, schedule_id) -> list[dict]:
    """Check for excessive consecutive work blocks in a day (soft constraint)."""
    violations = []

    result = await db.execute(
        select(ScheduleAssignment)
        .where(ScheduleAssignment.schedule_id == schedule_id)
        .order_by(ScheduleAssignment.staff_id, ScheduleAssignment.date)
    )
    assignments = result.scalars().all()

    # Group by staff_id and date
    by_staff_date: dict[tuple, list] = defaultdict(list)
    for a in assignments:
        if a.task_type_code == "off":
            continue
        by_staff_date[(str(a.staff_id), str(a.date))].append(a.time_block)

    # Fetch staff names
    staff_ids = {sid for sid, _ in by_staff_date.keys()}
    if staff_ids:
        staff_result = await db.execute(select(Staff).where(Staff.id.in_(staff_ids)))
        staff_names = {str(s.id): s.name for s in staff_result.scalars().all()}
    else:
        staff_names = {}

    for (staff_id, date_str), blocks in by_staff_date.items():
        work_blocks = [b for b in blocks if b != "lunch"]
        if len(work_blocks) >= 6:
            staff_name = staff_names.get(staff_id, "不明")
            violations.append({
                "type": "soft",
                "description": f"長時間勤務: {staff_name}は{date_str}に{len(work_blocks)}ブロック連続で勤務しています",
                "affected_date": date_str,
                "affected_time_block": None,
                "affected_staff": [staff_id],
                "severity": 400,
                "suggestion": "勤務ブロック数を減らすか、休憩を入れることを検討してください。",
            })
    return violations


async def _check_required_events(db: AsyncSession, schedule_id) -> list[dict]:
    """Check that all required-priority events have been assigned (have assignment with event_id)."""
    violations = []

    event_result = await db.execute(
        select(Event).where(
            Event.schedule_id == schedule_id,
            Event.priority == "required",
            Event.status.notin_(["hold", "done"]),
        )
    )
    required_events = list(event_result.scalars().all())
    if not required_events:
        return violations

    # Get all event_ids that appear in assignments for this schedule
    assign_result = await db.execute(
        select(ScheduleAssignment.event_id).where(
            ScheduleAssignment.schedule_id == schedule_id,
            ScheduleAssignment.event_id.isnot(None),
        )
    )
    assigned_event_ids = {row[0] for row in assign_result.all()}

    for event in required_events:
        if event.id not in assigned_event_ids:
            desc_parts = []
            if event.type_code:
                desc_parts.append(event.type_code)
            if event.subject_name:
                desc_parts.append(event.subject_name)
            label = " / ".join(desc_parts) if desc_parts else str(event.id)[:8]
            violations.append({
                "type": "hard",
                "description": f"必須イベント未配置: {label}",
                "affected_date": None,
                "affected_time_block": None,
                "affected_staff": [],
                "severity": 950,
                "suggestion": "このイベントをスケジュールに配置してください。",
                "event_id": str(event.id),
            })

    return violations


async def _check_event_constraints(db: AsyncSession, schedule_id) -> list[dict]:
    """Check that event-bearing assignments have staff with required skills."""
    violations = []

    # Get all assignments with event_id
    assign_result = await db.execute(
        select(ScheduleAssignment).where(
            ScheduleAssignment.schedule_id == schedule_id,
            ScheduleAssignment.event_id.isnot(None),
        )
    )
    event_assignments = list(assign_result.scalars().all())
    if not event_assignments:
        return violations

    # Load events
    event_ids = {a.event_id for a in event_assignments}
    event_result = await db.execute(
        select(Event).where(Event.id.in_(event_ids))
    )
    event_map = {e.id: e for e in event_result.scalars().all()}

    # Load staff skills
    staff_ids = {a.staff_id for a in event_assignments}
    skill_result = await db.execute(
        select(StaffSkill).where(StaffSkill.staff_id.in_(staff_ids))
    )
    staff_skills_map: dict[str, set[str]] = defaultdict(set)
    for ss in skill_result.scalars().all():
        staff_skills_map[str(ss.staff_id)].add(ss.skill_code)

    # Load staff names
    staff_result = await db.execute(select(Staff).where(Staff.id.in_(staff_ids)))
    staff_names = {str(s.id): s.name for s in staff_result.scalars().all()}

    # Check each assignment
    seen: set[tuple[str, str]] = set()  # (event_id, staff_id) deduplicate across blocks
    for a in event_assignments:
        event = event_map.get(a.event_id)
        if not event:
            continue
        key = (str(a.event_id), str(a.staff_id))
        if key in seen:
            continue
        seen.add(key)

        required = event.required_skills or []
        if not required:
            continue
        s_skills = staff_skills_map.get(str(a.staff_id), set())
        missing = [r for r in required if r not in s_skills]
        if missing:
            staff_name = staff_names.get(str(a.staff_id), "不明")
            violations.append({
                "type": "hard",
                "description": (
                    f"イベントスキル不足: {staff_name}にイベント({event.type_code or '?'})の"
                    f"必須スキル({', '.join(missing)})がありません"
                ),
                "affected_date": str(a.date),
                "affected_time_block": a.time_block,
                "affected_staff": [str(a.staff_id)],
                "severity": 900,
                "suggestion": f"必須スキル{', '.join(missing)}を持つ職員に変更してください。",
                "event_id": str(event.id),
            })

    return violations


async def _check_resource_capacity_schedule(db: AsyncSession, schedule_id) -> list[dict]:
    """Check resource capacity limits for all bookings in this schedule."""
    violations = []

    # Get assignments for this schedule
    assign_result = await db.execute(
        select(ScheduleAssignment.id).where(
            ScheduleAssignment.schedule_id == schedule_id,
        )
    )
    assignment_ids = [row[0] for row in assign_result.all()]
    if not assignment_ids:
        return violations

    # Get bookings for these assignments
    booking_result = await db.execute(
        select(ResourceBooking).where(
            ResourceBooking.assignment_id.in_(assignment_ids)
        )
    )
    bookings = list(booking_result.scalars().all())
    if not bookings:
        return violations

    # Load resources
    resource_ids = {b.resource_id for b in bookings}
    res_result = await db.execute(
        select(Resource).where(Resource.id.in_(resource_ids))
    )
    resource_map = {r.id: r for r in res_result.scalars().all()}

    # Group bookings by (resource_id, date, time_block) and count
    grouped: dict[tuple, int] = defaultdict(int)
    for b in bookings:
        grouped[(b.resource_id, str(b.date), b.time_block)] += 1

    for (rid, date_str, tb), count in grouped.items():
        resource = resource_map.get(rid)
        if not resource:
            continue
        if count > resource.capacity:
            violations.append({
                "type": "hard",
                "description": (
                    f"リソース容量超過: {resource.name}({resource.type}) {date_str} {tb}"
                    f" — {count}/{resource.capacity}"
                ),
                "affected_date": date_str,
                "affected_time_block": tb,
                "affected_staff": [],
                "severity": 850,
                "suggestion": f"リソース{resource.name}の予約を{resource.capacity}件以下に減らしてください。",
            })

    return violations


async def _check_rules(db: AsyncSession, schedule_id) -> list[dict]:
    """Check active rules against the schedule assignments."""
    violations = []

    rule_result = await db.execute(
        select(Rule).where(Rule.is_active == True)  # noqa: E712
    )
    rules = rule_result.scalars().all()
    if not rules:
        return violations

    assign_result = await db.execute(
        select(ScheduleAssignment)
        .where(ScheduleAssignment.schedule_id == schedule_id)
    )
    assignments = assign_result.scalars().all()
    if not assignments:
        return violations

    staff_ids = {a.staff_id for a in assignments}
    staff_result = await db.execute(select(Staff).where(Staff.id.in_(staff_ids)))
    staff_map = {str(s.id): s for s in staff_result.scalars().all()}

    tt_result = await db.execute(select(TaskType))
    task_type_map = {t.code: t for t in tt_result.scalars().all()}

    for rule in rules:
        rule_violations = _evaluate_rule(rule, assignments, staff_map, task_type_map)
        violations.extend(rule_violations)

    return violations


def _evaluate_rule(
    rule: Rule,
    assignments: list,
    staff_map: dict,
    task_type_map: dict,
) -> list[dict]:
    """Evaluate a single rule against assignments."""
    rule_type = rule.template_type

    if rule_type == "headcount":
        return _eval_headcount_rule(rule, assignments, task_type_map)
    elif rule_type == "availability":
        return _eval_availability_rule(rule, assignments, staff_map)
    elif rule_type == "preference":
        return _eval_preference_rule(rule, assignments, staff_map)
    elif rule_type == "recurring":
        return _eval_recurring_rule(rule, assignments, task_type_map)
    elif rule_type == "specific_date":
        return _eval_specific_date_rule(rule, assignments, staff_map, task_type_map)
    return []


def _eval_headcount_rule(rule: Rule, assignments: list, task_type_map: dict) -> list[dict]:
    """Evaluate headcount-type rules."""
    violations = []
    body = rule.body or {}
    event_code = body.get("event_code") or body.get("task_type_code")
    min_staff = body.get("min_staff")
    max_staff = body.get("max_staff")

    if not event_code:
        return violations

    grouped: dict[tuple, list] = defaultdict(list)
    for a in assignments:
        if a.task_type_code == event_code:
            grouped[(str(a.date), a.time_block)].append(a)

    for (date_str, tb), assigns in grouped.items():
        count = len(assigns)
        if min_staff and count < min_staff:
            tt = task_type_map.get(event_code)
            display = tt.display_name if tt else event_code
            violations.append({
                "type": rule.hard_or_soft,
                "description": f"ルール違反「{rule.natural_text}」: {date_str} {tb} の{display}に{count}名（最低{min_staff}名必要）",
                "affected_date": date_str,
                "affected_time_block": tb,
                "affected_staff": [str(a.staff_id) for a in assigns],
                "severity": rule.weight if rule.hard_or_soft == "soft" else 1000,
                "suggestion": f"あと{min_staff - count}名追加してください。",
                "rule_id": str(rule.id),
            })
        if max_staff and count > max_staff:
            tt = task_type_map.get(event_code)
            display = tt.display_name if tt else event_code
            violations.append({
                "type": rule.hard_or_soft,
                "description": f"ルール違反「{rule.natural_text}」: {date_str} {tb} の{display}に{count}名（最大{max_staff}名）",
                "affected_date": date_str,
                "affected_time_block": tb,
                "affected_staff": [str(a.staff_id) for a in assigns],
                "severity": rule.weight if rule.hard_or_soft == "soft" else 1000,
                "suggestion": f"{count - max_staff}名減らしてください。",
                "rule_id": str(rule.id),
            })
    return violations


def _eval_availability_rule(rule: Rule, assignments: list, staff_map: dict) -> list[dict]:
    """Evaluate availability-type rules."""
    violations = []
    body = rule.body or {}

    staff_name = body.get("staff_name")
    blocked_weekdays = body.get("blocked_weekdays", [])
    blocked_blocks = body.get("blocked_blocks", [])

    if not staff_name:
        return violations

    target_staff_ids = [sid for sid, s in staff_map.items() if s.name == staff_name]

    for a in assignments:
        staff_id_str = str(a.staff_id)
        if staff_id_str not in target_staff_ids:
            continue
        if a.task_type_code == "off":
            continue

        from datetime import date as date_type
        d = a.date if isinstance(a.date, date_type) else date_type.fromisoformat(str(a.date))

        if d.weekday() in blocked_weekdays:
            if not blocked_blocks or a.time_block in blocked_blocks:
                violations.append({
                    "type": rule.hard_or_soft,
                    "description": f"ルール違反「{rule.natural_text}」: {staff_name}が勤務不可の時間帯に割り当てられています",
                    "affected_date": str(a.date),
                    "affected_time_block": a.time_block,
                    "affected_staff": [staff_id_str],
                    "severity": rule.weight if rule.hard_or_soft == "soft" else 1000,
                    "suggestion": f"{staff_name}をこの時間帯から外してください。",
                    "rule_id": str(rule.id),
                })
    return violations


def _eval_preference_rule(rule: Rule, assignments: list, staff_map: dict) -> list[dict]:
    """Evaluate preference-type rules."""
    violations = []
    body = rule.body or {}

    preferred_staff = body.get("preferred_staff_name")
    task_code = body.get("task_type_code")
    weekday = body.get("weekday")

    if not (preferred_staff and task_code):
        return violations

    from datetime import date as date_type

    grouped: dict[tuple, list[str]] = defaultdict(list)
    for a in assignments:
        if a.task_type_code == task_code:
            grouped[(str(a.date), a.time_block)].append(str(a.staff_id))

    preferred_ids = [sid for sid, s in staff_map.items() if s.name == preferred_staff]

    for (date_str, tb), staff_ids in grouped.items():
        if weekday is not None:
            d = date_type.fromisoformat(date_str)
            if d.weekday() != weekday:
                continue
        if not any(pid in staff_ids for pid in preferred_ids):
            violations.append({
                "type": "soft",
                "description": f"ルール違反「{rule.natural_text}」: {preferred_staff}が割り当てられていません",
                "affected_date": date_str,
                "affected_time_block": tb,
                "affected_staff": staff_ids,
                "severity": rule.weight,
                "suggestion": f"{preferred_staff}をこの枠に割り当てることを検討してください。",
                "rule_id": str(rule.id),
            })
    return violations


def _eval_recurring_rule(
    rule: Rule,
    assignments: list,
    task_type_map: dict,
) -> list[dict]:
    """Evaluate recurring-type rules (e.g., 'every Tuesday AM needs 2 daycare staff')."""
    violations = []
    body = rule.body or {}

    weekdays = body.get("weekdays", [])  # list of int (0=Mon..6=Sun)
    task_code = body.get("task_type_code")
    min_staff = body.get("min_staff", 0)
    time_blocks = body.get("time_blocks", [])  # list of time_block strings

    if not weekdays or not task_code:
        return violations

    from datetime import date as date_type

    # Group assignments by (date, time_block) for the matching task_code
    grouped: dict[tuple[str, str], int] = defaultdict(int)
    all_slots: set[tuple[str, str]] = set()

    for a in assignments:
        d = a.date if isinstance(a.date, date_type) else date_type.fromisoformat(str(a.date))
        if d.weekday() not in weekdays:
            continue
        if time_blocks and a.time_block not in time_blocks:
            continue
        all_slots.add((str(a.date), a.time_block))
        if a.task_type_code == task_code:
            grouped[(str(a.date), a.time_block)] += 1

    # Check all affected slots for understaffing
    for (date_str, tb) in all_slots:
        count = grouped.get((date_str, tb), 0)
        if min_staff and count < min_staff:
            tt = task_type_map.get(task_code)
            display = tt.display_name if tt else task_code
            violations.append({
                "type": rule.hard_or_soft,
                "description": (
                    f"ルール違反「{rule.natural_text}」: {date_str} {tb} の"
                    f"{display}に{count}名（最低{min_staff}名必要）"
                ),
                "affected_date": date_str,
                "affected_time_block": tb,
                "affected_staff": [],
                "severity": rule.weight if rule.hard_or_soft == "soft" else 1000,
                "suggestion": f"あと{min_staff - count}名追加してください。",
                "rule_id": str(rule.id),
            })

    return violations


def _eval_specific_date_rule(
    rule: Rule,
    assignments: list,
    staff_map: dict,
    task_type_map: dict,
) -> list[dict]:
    """Evaluate specific_date rules (e.g., 'on 2025-05-15 PM, need 3 daycare staff incl. 山田')."""
    violations = []
    body = rule.body or {}

    target_date = body.get("date")
    task_code = body.get("task_type_code")
    min_staff = body.get("min_staff", 0)
    required_staff_names = body.get("required_staff_names", [])
    time_block = body.get("time_block")

    if not target_date:
        return violations

    from datetime import date as date_type

    # Filter assignments for this date (and optionally time_block)
    matched: list = []
    for a in assignments:
        d = a.date if isinstance(a.date, date_type) else date_type.fromisoformat(str(a.date))
        if str(d) != str(target_date):
            continue
        if time_block and a.time_block != time_block:
            continue
        if task_code and a.task_type_code != task_code:
            continue
        matched.append(a)

    # Check min_staff
    if min_staff and len(matched) < min_staff:
        tt = task_type_map.get(task_code) if task_code else None
        display = tt.display_name if tt else (task_code or "業務")
        violations.append({
            "type": rule.hard_or_soft,
            "description": (
                f"ルール違反「{rule.natural_text}」: {target_date}"
                f"{' ' + time_block if time_block else ''} の"
                f"{display}に{len(matched)}名（最低{min_staff}名必要）"
            ),
            "affected_date": str(target_date),
            "affected_time_block": time_block,
            "affected_staff": [str(a.staff_id) for a in matched],
            "severity": rule.weight if rule.hard_or_soft == "soft" else 1000,
            "suggestion": f"あと{min_staff - len(matched)}名追加してください。",
            "rule_id": str(rule.id),
        })

    # Check required_staff_names
    if required_staff_names:
        assigned_staff_ids = {str(a.staff_id) for a in matched}
        assigned_names = {staff_map[sid].name for sid in assigned_staff_ids if sid in staff_map}
        for name in required_staff_names:
            if name not in assigned_names:
                violations.append({
                    "type": rule.hard_or_soft,
                    "description": (
                        f"ルール違反「{rule.natural_text}」: {target_date}"
                        f"{' ' + time_block if time_block else ''} に"
                        f"{name}が割り当てられていません"
                    ),
                    "affected_date": str(target_date),
                    "affected_time_block": time_block,
                    "affected_staff": [],
                    "severity": rule.weight if rule.hard_or_soft == "soft" else 1000,
                    "suggestion": f"{name}をこの枠に割り当ててください。",
                    "rule_id": str(rule.id),
                })

    return violations


async def validate_schedule(db: AsyncSession, schedule_id) -> list[dict]:
    """Run all validation checks on a schedule. Returns list of violations."""
    violations = []

    # 1. Duplicate assignments (hard)
    violations.extend(await _check_duplicates(db, schedule_id))

    # 2. Skill requirements (hard)
    violations.extend(await _check_skill_requirements(db, schedule_id))

    # 3. Minimum staff per task type (soft)
    violations.extend(await _check_min_staff(db, schedule_id))

    # 4. Visit transport requirements (hard/soft)
    violations.extend(await _check_visit_transport(db, schedule_id))

    # 5. Consecutive work blocks (soft)
    violations.extend(await _check_consecutive_work(db, schedule_id))

    # 6. Custom rules from rules table
    violations.extend(await _check_rules(db, schedule_id))

    # 7. Required events unassigned (hard)
    violations.extend(await _check_required_events(db, schedule_id))

    # 8. Event skill constraints (hard)
    violations.extend(await _check_event_constraints(db, schedule_id))

    # 9. Resource capacity (hard)
    violations.extend(await _check_resource_capacity_schedule(db, schedule_id))

    return violations
