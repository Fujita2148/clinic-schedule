"""Schedule service — grid data assembly."""

import calendar
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.day_program import DayProgram
from app.models.master import TimeBlockMaster
from app.models.schedule import Schedule, ScheduleAssignment
from app.models.staff import Staff
from app.models.task_type import TaskType
from app.schemas.schedule import GridCell, GridData, GridRow

TIME_BLOCK_ORDER = ["am", "lunch", "pm", "15", "16", "17", "18plus"]


async def build_grid_data(db: AsyncSession, schedule: Schedule) -> GridData:
    year, month = map(int, schedule.year_month.split("-"))
    _, last_day = calendar.monthrange(year, month)

    # Fetch staff
    staff_result = await db.execute(
        select(Staff).where(Staff.is_active == True).order_by(Staff.name)  # noqa: E712
    )
    staff_list = staff_result.scalars().all()

    # Fetch time blocks
    tb_result = await db.execute(select(TimeBlockMaster).order_by(TimeBlockMaster.sort_order))
    time_blocks = tb_result.scalars().all()
    tb_display = {tb.code: tb.display_name for tb in time_blocks}

    # Fetch task types for display name lookup
    tt_result = await db.execute(select(TaskType))
    task_types = tt_result.scalars().all()
    tt_display = {tt.code: tt.display_name for tt in task_types}

    # Fetch assignments
    assign_result = await db.execute(
        select(ScheduleAssignment).where(ScheduleAssignment.schedule_id == schedule.id)
    )
    assignments = assign_result.scalars().all()

    # Index assignments by (date, time_block, staff_id)
    assign_index: dict[tuple, ScheduleAssignment] = {}
    for a in assignments:
        assign_index[(a.date, a.time_block, str(a.staff_id))] = a

    # Fetch day programs
    dp_result = await db.execute(
        select(DayProgram).where(DayProgram.schedule_id == schedule.id)
    )
    day_programs = dp_result.scalars().all()
    dp_index: dict[tuple, DayProgram] = {}
    for dp in day_programs:
        dp_index[(dp.date, dp.time_block)] = dp

    # Build rows
    rows: list[GridRow] = []
    for day_num in range(1, last_day + 1):
        current_date = date(year, month, day_num)
        for block_code in TIME_BLOCK_ORDER:
            dp = dp_index.get((current_date, block_code))
            cells: dict[str, GridCell] = {}
            for staff in staff_list:
                sid = str(staff.id)
                a = assign_index.get((current_date, block_code, sid))
                if a:
                    cells[sid] = GridCell(
                        assignment_id=a.id,
                        task_type_code=a.task_type_code,
                        task_type_display_name=tt_display.get(a.task_type_code) if a.task_type_code else None,
                        display_text=a.display_text,
                        status_color=a.status_color,
                        is_locked=a.is_locked,
                        source=a.source,
                    )
                else:
                    cells[sid] = GridCell()

            rows.append(GridRow(
                date=current_date,
                time_block=block_code,
                time_block_display=tb_display.get(block_code, block_code),
                program_title=dp.program_title if dp else None,
                is_nightcare=dp.is_nightcare if dp else False,
                summary_text=dp.summary_text if dp else None,
                cells=cells,
            ))

    return GridData(
        schedule_id=schedule.id,
        year_month=schedule.year_month,
        staff_list=[
            {"id": str(s.id), "name": s.name, "job_category": s.job_category}
            for s in staff_list
        ],
        rows=rows,
    )
