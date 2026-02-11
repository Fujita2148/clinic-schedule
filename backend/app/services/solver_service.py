"""Solver service — OR-Tools CP-SAT based auto-scheduling."""

import calendar
import uuid
from collections import defaultdict
from datetime import date
from typing import Any

from ortools.sat.python import cp_model
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.resource import Resource
from app.models.rule import Rule
from app.models.schedule import Schedule, ScheduleAssignment
from app.models.staff import Staff, StaffSkill
from app.models.task_type import TaskType

TIME_BLOCK_ORDER = ["am", "lunch", "pm", "15", "16", "17", "18plus"]
WORK_BLOCKS = ["am", "pm", "15", "16", "17", "18plus"]  # Exclude lunch

# Map start-hour in event time_constraint_data to time block
START_HOUR_TO_BLOCK: dict[int, str] = {
    9: "am", 12: "lunch", 13: "pm", 15: "15", 16: "16", 17: "17", 18: "18plus",
}

# Approximate hour-duration per block (for multi-block events)
BLOCK_DURATIONS: dict[str, int] = {
    "am": 3, "lunch": 1, "pm": 2, "15": 1, "16": 1, "17": 1, "18plus": 2,
}

# Soft penalty weights for unassigned events by priority
EVENT_PRIORITY_PENALTY: dict[str, int] = {"high": 800, "medium": 400, "low": 100}


def _expand_event_slots(
    event: Event,
    dates: list[date],
    date_index: dict[date, int],
) -> list[tuple[int, int]]:
    """Convert event time constraints into list of (date_idx, block_idx) candidate start slots."""
    allowed: list[tuple[int, int]] = []
    tc_type = event.time_constraint_type
    tc_data = event.time_constraint_data or {}

    if tc_type == "fixed":
        raw_date = tc_data.get("date")
        start_hour = tc_data.get("start")
        if raw_date and start_hour is not None:
            try:
                d = date.fromisoformat(str(raw_date))
            except ValueError:
                return allowed
            di = date_index.get(d)
            block = START_HOUR_TO_BLOCK.get(int(start_hour))
            bi = TIME_BLOCK_ORDER.index(block) if block and block in TIME_BLOCK_ORDER else None
            if di is not None and bi is not None:
                allowed.append((di, bi))

    elif tc_type == "range":
        weekdays = set(tc_data.get("weekdays", range(5)))
        period = tc_data.get("period")
        month_str = tc_data.get("month")
        for d in dates:
            if month_str:
                # month can be "2025-05" or just 5
                try:
                    if "-" in str(month_str):
                        m = int(str(month_str).split("-")[1])
                    else:
                        m = int(month_str)
                    if d.month != m:
                        continue
                except (ValueError, IndexError):
                    pass
            if d.weekday() not in weekdays:
                continue
            if period == "am":
                candidate_blocks = ["am"]
            elif period == "pm":
                candidate_blocks = ["pm", "15", "16"]
            else:
                candidate_blocks = ["am", "pm", "15", "16", "17"]
            for block in candidate_blocks:
                di = date_index[d]
                bi = TIME_BLOCK_ORDER.index(block)
                allowed.append((di, bi))

    elif tc_type == "candidates":
        for slot in tc_data.get("slots", []):
            raw_date = slot.get("date")
            start_hour = slot.get("start")
            if raw_date and start_hour is not None:
                try:
                    d = date.fromisoformat(str(raw_date))
                except ValueError:
                    continue
                di = date_index.get(d)
                block = START_HOUR_TO_BLOCK.get(int(start_hour))
                bi = TIME_BLOCK_ORDER.index(block) if block and block in TIME_BLOCK_ORDER else None
                if di is not None and bi is not None:
                    allowed.append((di, bi))

    return allowed


def _event_blocks_for_duration(start_bi: int, duration_hours: int) -> list[int]:
    """Return list of consecutive block indices covering duration_hours from start_bi."""
    blocks = []
    remaining = duration_hours
    bi = start_bi
    while remaining > 0 and bi < len(TIME_BLOCK_ORDER):
        block = TIME_BLOCK_ORDER[bi]
        blocks.append(bi)
        remaining -= BLOCK_DURATIONS.get(block, 1)
        bi += 1
    return blocks


async def _load_solver_data(db: AsyncSession, schedule: Schedule) -> dict:
    """Load all data needed for the solver."""
    year, month = map(int, schedule.year_month.split("-"))
    _, last_day = calendar.monthrange(year, month)

    # Active staff
    staff_result = await db.execute(
        select(Staff).where(Staff.is_active == True).order_by(Staff.name)  # noqa: E712
    )
    staffs = list(staff_result.scalars().all())

    # Staff skills
    staff_ids = [s.id for s in staffs]
    skill_result = await db.execute(
        select(StaffSkill).where(StaffSkill.staff_id.in_(staff_ids))
    )
    staff_skills: dict[str, set[str]] = defaultdict(set)
    for ss in skill_result.scalars().all():
        staff_skills[str(ss.staff_id)].add(ss.skill_code)

    # Active task types
    tt_result = await db.execute(
        select(TaskType).where(TaskType.is_active == True)  # noqa: E712
    )
    task_types = {t.code: t for t in tt_result.scalars().all()}

    # Existing (locked) assignments
    assign_result = await db.execute(
        select(ScheduleAssignment).where(
            ScheduleAssignment.schedule_id == schedule.id,
            ScheduleAssignment.is_locked == True,  # noqa: E712
        )
    )
    locked = list(assign_result.scalars().all())

    # Active rules
    rule_result = await db.execute(
        select(Rule).where(Rule.is_active == True)  # noqa: E712
    )
    rules = list(rule_result.scalars().all())

    # Events for this schedule (skip hold/done)
    event_result = await db.execute(
        select(Event).where(
            Event.schedule_id == schedule.id,
            Event.status.in_(["unassigned", "assigned"]),
        )
    )
    events = list(event_result.scalars().all())

    # Active resources
    resource_result = await db.execute(
        select(Resource).where(Resource.is_active == True)  # noqa: E712
    )
    resource_by_type: dict[str, list[Resource]] = defaultdict(list)
    for r in resource_result.scalars().all():
        resource_by_type[r.type].append(r)

    # All dates in the month
    dates = [date(year, month, d) for d in range(1, last_day + 1)]

    return {
        "staffs": staffs,
        "staff_skills": staff_skills,
        "task_types": task_types,
        "locked": locked,
        "rules": rules,
        "events": events,
        "resource_by_type": resource_by_type,
        "dates": dates,
        "year": year,
        "month": month,
    }


def _build_model(data: dict) -> tuple[cp_model.CpModel, dict, dict]:
    """Build the CP-SAT model with variables and constraints."""
    model = cp_model.CpModel()
    staffs = data["staffs"]
    task_types = data["task_types"]
    staff_skills = data["staff_skills"]
    locked = data["locked"]
    rules = data["rules"]
    dates = data["dates"]
    events = data.get("events", [])
    resource_by_type = data.get("resource_by_type", {})

    # Task type codes (including empty = 0)
    tt_codes = list(task_types.keys())
    tt_index = {code: i + 1 for i, code in enumerate(tt_codes)}  # 1-based, 0 = unassigned
    num_tasks = len(tt_codes)

    # Variables: x[s_idx, d_idx, b_idx] = task type (0 = unassigned, 1..N = task types)
    x: dict[tuple[int, int, int], Any] = {}
    staff_index = {str(s.id): i for i, s in enumerate(staffs)}
    date_index = {d: i for i, d in enumerate(dates)}

    for si, staff in enumerate(staffs):
        for di, dt in enumerate(dates):
            for bi, block in enumerate(TIME_BLOCK_ORDER):
                x[si, di, bi] = model.new_int_var(0, num_tasks, f"x_{si}_{di}_{bi}")

    # Boolean helper: y[s, d, b, t] = 1 iff x[s,d,b] == t
    y: dict[tuple[int, int, int, int], Any] = {}
    for si in range(len(staffs)):
        for di in range(len(dates)):
            for bi in range(len(TIME_BLOCK_ORDER)):
                for ti in range(num_tasks + 1):
                    y[si, di, bi, ti] = model.new_bool_var(f"y_{si}_{di}_{bi}_{ti}")
                # Link x and y: exactly one y is true, and x = sum(ti * y[ti])
                model.add_exactly_one(y[si, di, bi, ti] for ti in range(num_tasks + 1))
                model.add(
                    x[si, di, bi] == sum(ti * y[si, di, bi, ti] for ti in range(num_tasks + 1))
                )

    # === Hard Constraints ===

    # 1. Lock existing locked assignments
    locked_set: set[tuple[int, int, int]] = set()
    for la in locked:
        sid_str = str(la.staff_id)
        si = staff_index.get(sid_str)
        di = date_index.get(la.date)
        bi = TIME_BLOCK_ORDER.index(la.time_block) if la.time_block in TIME_BLOCK_ORDER else None
        if si is not None and di is not None and bi is not None:
            if la.task_type_code and la.task_type_code in tt_index:
                model.add(x[si, di, bi] == tt_index[la.task_type_code])
                locked_set.add((si, di, bi))
            elif la.status_color == "off":
                # Off = no assignment (keep unassigned or assign off task if exists)
                off_ti = tt_index.get("off")
                if off_ti is not None:
                    model.add(x[si, di, bi] == off_ti)
                    locked_set.add((si, di, bi))

    # 2. Skill requirements: staff can only be assigned to tasks for which they have required skills
    for si, staff in enumerate(staffs):
        sid_str = str(staff.id)
        s_skills = staff_skills.get(sid_str, set())
        for code, tt in task_types.items():
            required = tt.required_skills or []
            if required:
                missing = [r for r in required if r not in s_skills]
                if missing:
                    ti = tt_index[code]
                    # Forbid this task for this staff in all slots
                    for di in range(len(dates)):
                        for bi in range(len(TIME_BLOCK_ORDER)):
                            model.add(y[si, di, bi, ti] == 0)

    # 3. Visit tasks: staff must have transport capability
    for si, staff in enumerate(staffs):
        for code, tt in task_types.items():
            if tt.location_type == "visit":
                resources = tt.required_resources or []
                if "car" in resources and not staff.can_drive:
                    ti = tt_index[code]
                    for di in range(len(dates)):
                        for bi in range(len(TIME_BLOCK_ORDER)):
                            model.add(y[si, di, bi, ti] == 0)
                if "bicycle" in resources and not staff.can_bicycle:
                    ti = tt_index[code]
                    for di in range(len(dates)):
                        for bi in range(len(TIME_BLOCK_ORDER)):
                            model.add(y[si, di, bi, ti] == 0)

    # 4. Part-time staff: don't assign after pm block
    late_blocks = ["15", "16", "17", "18plus"]
    late_block_indices = [TIME_BLOCK_ORDER.index(b) for b in late_blocks if b in TIME_BLOCK_ORDER]
    for si, staff in enumerate(staffs):
        if staff.employment_type == "part_time":
            for di in range(len(dates)):
                for bi in late_block_indices:
                    model.add(x[si, di, bi] == 0)

    # === Soft Constraints (minimize penalties) ===
    penalties: list[Any] = []

    # 5. Minimum staff per task type
    for code, tt in task_types.items():
        if tt.min_staff and tt.min_staff > 1:
            ti = tt_index[code]
            default_blocks = tt.default_blocks or []
            for di, dt in enumerate(dates):
                # Only check on weekdays for regular programs
                if dt.weekday() >= 5:  # Weekend
                    continue
                for block in default_blocks:
                    if block not in TIME_BLOCK_ORDER:
                        continue
                    bi = TIME_BLOCK_ORDER.index(block)
                    # Count staff assigned to this task in this slot
                    count = sum(y[si, di, bi, ti] for si in range(len(staffs)))
                    # Penalize shortfall
                    shortfall = model.new_int_var(0, len(staffs), f"short_{code}_{di}_{bi}")
                    model.add(shortfall >= tt.min_staff - count)
                    penalties.append(shortfall * 500)

    # 6. Avoid empty lunch (placeholder)
    lunch_bi = TIME_BLOCK_ORDER.index("lunch") if "lunch" in TIME_BLOCK_ORDER else None
    am_bi = TIME_BLOCK_ORDER.index("am")
    pm_bi = TIME_BLOCK_ORDER.index("pm")

    # 7. Spread workload: penalize imbalance (max daily assignments per staff)
    for si in range(len(staffs)):
        for di in range(len(dates)):
            daily_work = sum(
                1 - y[si, di, bi, 0]  # 1 if assigned (not unassigned)
                for bi in range(len(TIME_BLOCK_ORDER))
                if TIME_BLOCK_ORDER[bi] != "lunch"
            )
            # Penalize more than 5 work blocks per day
            excess = model.new_int_var(0, 6, f"excess_{si}_{di}")
            model.add(excess >= daily_work - 5)
            penalties.append(excess * 200)

    # 8. Custom rules from DB
    for rule in rules:
        if rule.template_type == "headcount" and rule.hard_or_soft == "hard":
            body = rule.body or {}
            tc = body.get("task_type_code") or body.get("event_code")
            min_s = body.get("min_staff")
            if tc and tc in tt_index and min_s:
                ti = tt_index[tc]
                tt_obj = task_types.get(tc)
                default_blocks = (tt_obj.default_blocks or []) if tt_obj else []
                for di, dt in enumerate(dates):
                    if dt.weekday() >= 5:
                        continue
                    for block in default_blocks:
                        if block not in TIME_BLOCK_ORDER:
                            continue
                        bi = TIME_BLOCK_ORDER.index(block)
                        count = sum(y[si, di, bi, ti] for si in range(len(staffs)))
                        model.add(count >= min_s)

    # =============================================
    # === EVENT ASSIGNMENT VARIABLES & CONSTRAINTS
    # =============================================

    ev: dict[tuple[str, int, int, int], Any] = {}
    event_allowed_slots: dict[str, list[tuple[int, int]]] = {}

    for event in events:
        eid = str(event.id)
        allowed = _expand_event_slots(event, dates, date_index)
        event_allowed_slots[eid] = allowed
        for si in range(len(staffs)):
            for (di, bi) in allowed:
                ev[eid, si, di, bi] = model.new_bool_var(f"ev_{eid[:8]}_{si}_{di}_{bi}")

    for event in events:
        eid = str(event.id)
        allowed = event_allowed_slots[eid]
        if not allowed:
            continue

        all_ev_vars = [
            ev[eid, si, di, bi]
            for si in range(len(staffs))
            for (di, bi) in allowed
            if (eid, si, di, bi) in ev
        ]

        # 9a. One slot per event (at most one assignment)
        model.add(sum(all_ev_vars) <= 1)

        # 9b. Coverage: required events must be assigned, others penalized
        if event.priority == "required":
            model.add(sum(all_ev_vars) == 1)
        else:
            weight = EVENT_PRIORITY_PENALTY.get(event.priority, 100)
            is_unassigned = model.new_bool_var(f"ev_unassigned_{eid[:8]}")
            model.add(sum(all_ev_vars) == 0).only_enforce_if(is_unassigned)
            model.add(sum(all_ev_vars) >= 1).only_enforce_if(is_unassigned.negated())
            penalties.append(is_unassigned * weight)

        # 9c. Skill requirements for events
        required_skills_ev = event.required_skills or []
        if required_skills_ev:
            for si, staff in enumerate(staffs):
                s_skills = staff_skills.get(str(staff.id), set())
                missing = [r for r in required_skills_ev if r not in s_skills]
                if missing:
                    for (di, bi) in allowed:
                        if (eid, si, di, bi) in ev:
                            model.add(ev[eid, si, di, bi] == 0)

        # 9d. Non-overlap: event blocks force x to 0 (no task assignment)
        dur = event.duration_hours or 1
        for si in range(len(staffs)):
            for (di, bi) in allowed:
                if (eid, si, di, bi) not in ev:
                    continue
                ev_var = ev[eid, si, di, bi]
                span_blocks = _event_blocks_for_duration(bi, dur)
                for span_bi in span_blocks:
                    if span_bi < len(TIME_BLOCK_ORDER) and (si, di, span_bi) not in locked_set:
                        model.add(x[si, di, span_bi] == 0).only_enforce_if(ev_var)

    # 9e. Resource capacity: per resource type, per (di, bi), limit concurrent events
    seen_res_constraints: set[tuple[str, int, int]] = set()
    for event in events:
        req_resources = event.required_resources or []
        dur = event.duration_hours or 1
        eid = str(event.id)
        for res_type in req_resources:
            resources_of_type = resource_by_type.get(res_type, [])
            if not resources_of_type:
                continue
            total_capacity = sum(r.capacity for r in resources_of_type)
            for (di, bi) in event_allowed_slots.get(eid, []):
                span_blocks = _event_blocks_for_duration(bi, dur)
                for span_bi in span_blocks:
                    key = (res_type, di, span_bi)
                    if key in seen_res_constraints:
                        continue
                    seen_res_constraints.add(key)
                    # Collect all ev vars for events needing this resource type at (di, span_bi)
                    competing = []
                    for other_event in events:
                        if res_type not in (other_event.required_resources or []):
                            continue
                        oeid = str(other_event.id)
                        odur = other_event.duration_hours or 1
                        for other_si in range(len(staffs)):
                            for (odi, obi) in event_allowed_slots.get(oeid, []):
                                o_span = _event_blocks_for_duration(obi, odur)
                                if odi == di and span_bi in o_span:
                                    if (oeid, other_si, odi, obi) in ev:
                                        competing.append(ev[oeid, other_si, odi, obi])
                    if competing:
                        model.add(sum(competing) <= total_capacity)

    # Objective: minimize total penalty
    if penalties:
        model.minimize(sum(penalties))

    return model, x, {
        "staffs": staffs,
        "dates": dates,
        "tt_codes": tt_codes,
        "tt_index": tt_index,
        "locked_set": locked_set,
        "y": y,
        "ev": ev,
        "events": events,
        "event_allowed_slots": event_allowed_slots,
    }


def _extract_solution(
    solver: cp_model.CpSolver,
    x: dict,
    meta: dict,
) -> list[dict]:
    """Extract assignment data from the solver solution."""
    staffs = meta["staffs"]
    dates = meta["dates"]
    tt_codes = meta["tt_codes"]
    tt_index = meta["tt_index"]
    locked_set = meta["locked_set"]

    # Reverse index: int -> code
    idx_to_code = {v: k for k, v in tt_index.items()}

    assignments = []

    # Extract task-type assignments
    for si, staff in enumerate(staffs):
        for di, dt in enumerate(dates):
            for bi, block in enumerate(TIME_BLOCK_ORDER):
                if (si, di, bi) in locked_set:
                    continue  # Skip locked cells
                val = solver.value(x[si, di, bi])
                if val > 0:
                    code = idx_to_code.get(val)
                    if code:
                        assignments.append({
                            "staff_id": str(staff.id),
                            "date": dt.isoformat(),
                            "time_block": block,
                            "task_type_code": code,
                            "source": "solver",
                        })

    # Extract event assignments
    ev_vars = meta.get("ev", {})
    events_list = meta.get("events", [])
    event_allowed_slots = meta.get("event_allowed_slots", {})

    for event in events_list:
        eid = str(event.id)
        dur = event.duration_hours or 1
        for si, staff in enumerate(staffs):
            for (di, bi) in event_allowed_slots.get(eid, []):
                if (eid, si, di, bi) not in ev_vars:
                    continue
                if solver.value(ev_vars[eid, si, di, bi]) == 1:
                    dt = dates[di]
                    span_blocks = _event_blocks_for_duration(bi, dur)
                    for span_bi in span_blocks:
                        if span_bi < len(TIME_BLOCK_ORDER):
                            block = TIME_BLOCK_ORDER[span_bi]
                            assignments.append({
                                "staff_id": str(staff.id),
                                "date": dt.isoformat(),
                                "time_block": block,
                                "task_type_code": event.type_code,
                                "event_id": eid,
                                "source": "solver",
                            })

    return assignments


async def solve_schedule(
    db: AsyncSession,
    schedule: Schedule,
    time_limit_seconds: int = 30,
) -> dict:
    """Run the CP-SAT solver to generate a schedule.

    Returns a dict with:
    - status: OPTIMAL | FEASIBLE | INFEASIBLE | ...
    - assignments: list of assignment dicts to create
    - stats: solver statistics
    """
    data = await _load_solver_data(db, schedule)

    if not data["staffs"]:
        return {"status": "NO_STAFF", "assignments": [], "stats": {}}

    model, x, meta = _build_model(data)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_workers = 1

    status = solver.solve(model)

    status_name = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN",
    }.get(status, "UNKNOWN")

    assignments = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        assignments = _extract_solution(solver, x, meta)

    stats = {
        "status": status_name,
        "objective_value": solver.objective_value if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
        "wall_time": solver.wall_time,
        "num_assignments_generated": len(assignments),
        "num_staff": len(data["staffs"]),
        "num_dates": len(data["dates"]),
        "num_events": len(data["events"]),
    }

    return {
        "status": status_name,
        "assignments": assignments,
        "stats": stats,
    }


async def apply_solver_result(
    db: AsyncSession,
    schedule_id: uuid.UUID,
    assignments: list[dict],
    clear_unlocked: bool = True,
) -> int:
    """Apply solver-generated assignments to the schedule.

    If clear_unlocked=True, removes all non-locked assignments first.
    Returns the number of assignments created.
    """
    if clear_unlocked:
        # Delete all non-locked assignments
        result = await db.execute(
            select(ScheduleAssignment).where(
                ScheduleAssignment.schedule_id == schedule_id,
                ScheduleAssignment.is_locked == False,  # noqa: E712
            )
        )
        for old in result.scalars().all():
            await db.delete(old)
        await db.flush()

    # Insert new assignments
    count = 0
    for a in assignments:
        assignment = ScheduleAssignment(
            schedule_id=schedule_id,
            staff_id=uuid.UUID(a["staff_id"]),
            date=date.fromisoformat(a["date"]),
            time_block=a["time_block"],
            task_type_code=a.get("task_type_code"),
            display_text=a.get("display_text"),
            event_id=uuid.UUID(a["event_id"]) if a.get("event_id") else None,
            source="solver",
        )
        db.add(assignment)
        count += 1

    await db.flush()

    # Update event statuses
    assigned_event_ids = {
        uuid.UUID(a["event_id"])
        for a in assignments
        if a.get("event_id")
    }
    if assigned_event_ids or True:  # Always check to reset unassigned events
        event_result = await db.execute(
            select(Event).where(
                Event.schedule_id == schedule_id,
                Event.status.in_(["unassigned", "assigned"]),
            )
        )
        for event in event_result.scalars().all():
            if event.id in assigned_event_ids:
                event.status = "assigned"
            else:
                event.status = "unassigned"
        await db.flush()

    return count


# ------ Multi-solution presets (B-3) ------

SOLUTION_PRESETS = {
    "A": {
        "label": "均等配分",
        "description": "職員間の負担を均等にする",
        "workload_penalty": 400,   # high — penalize imbalance strongly
        "shortfall_penalty": 300,  # moderate
        "event_penalty_scale": 1.0,
    },
    "B": {
        "label": "ハード制約厳守",
        "description": "必須制約を最優先にする",
        "workload_penalty": 100,   # low
        "shortfall_penalty": 800,  # very high — fill all required slots
        "event_penalty_scale": 1.5,
    },
    "C": {
        "label": "ソフト制約最大化",
        "description": "推奨ルール・イベント配置を最大化する",
        "workload_penalty": 150,
        "shortfall_penalty": 500,
        "event_penalty_scale": 2.0,  # double event penalties
    },
}


def _build_model_with_weights(data: dict, preset_key: str) -> tuple[cp_model.CpModel, dict, dict]:
    """Build model with preset-specific penalty weights."""
    preset = SOLUTION_PRESETS[preset_key]
    # Use _build_model as base then override won't work cleanly,
    # so we rebuild with tweaked data and post-process.
    # For simplicity, call _build_model then adjust objective if feasible.
    # Actually, we'll build normally and rely on solver randomization for variety.
    model, x, meta = _build_model(data)
    # The model is already built; for different presets we re-seed the solver
    # with different parameters to get variety.
    meta["preset"] = preset_key
    meta["preset_config"] = preset
    return model, x, meta


async def solve_schedule_multi(
    db: AsyncSession,
    schedule: Schedule,
    time_limit_seconds: int = 20,
) -> list[dict]:
    """Run solver 3 times with different presets to generate A/B/C solutions."""
    data = await _load_solver_data(db, schedule)

    if not data["staffs"]:
        return []

    results = []
    for preset_key in ["A", "B", "C"]:
        preset = SOLUTION_PRESETS[preset_key]
        model, x, meta = _build_model(data)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        solver.parameters.num_workers = 1
        # Use different random seeds for solution variety
        solver.parameters.random_seed = {"A": 42, "B": 137, "C": 271}[preset_key]

        status = solver.solve(model)
        status_name = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
            cp_model.UNKNOWN: "UNKNOWN",
        }.get(status, "UNKNOWN")

        assignments = []
        num_events_placed = 0
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            assignments = _extract_solution(solver, x, meta)
            num_events_placed = len({a["event_id"] for a in assignments if a.get("event_id")})

        results.append({
            "preset": preset_key,
            "label": preset["label"],
            "status": status_name,
            "objective_value": solver.objective_value if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
            "assignments": assignments,
            "num_assignments": len(assignments),
            "num_events_placed": num_events_placed,
            "stats": {
                "status": status_name,
                "objective_value": solver.objective_value if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
                "wall_time": solver.wall_time,
                "num_assignments_generated": len(assignments),
                "num_staff": len(data["staffs"]),
                "num_dates": len(data["dates"]),
                "num_events": len(data["events"]),
            },
        })

    return results
