"""Export service — CSV generation."""

import csv
import io

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.day_program import DayProgram
from app.models.master import TimeBlockMaster
from app.models.schedule import Schedule, ScheduleAssignment
from app.models.staff import Staff
from app.services.schedule_service import TIME_BLOCK_ORDER

import calendar
from datetime import date


async def generate_csv(db: AsyncSession, schedule: Schedule) -> str:
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

    # Fetch assignments
    assign_result = await db.execute(
        select(ScheduleAssignment).where(ScheduleAssignment.schedule_id == schedule.id)
    )
    assignments = assign_result.scalars().all()
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

    WEEKDAYS_JP = ["月", "火", "水", "木", "金", "土", "日"]

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    header = ["日付", "曜日", "時間帯", "DNC", "予定"]
    header.extend([s.name for s in staff_list])
    writer.writerow(header)

    # Rows
    for day_num in range(1, last_day + 1):
        current_date = date(year, month, day_num)
        weekday = WEEKDAYS_JP[current_date.weekday()]
        for block_code in TIME_BLOCK_ORDER:
            dp = dp_index.get((current_date, block_code))
            row = [
                f"{month}/{day_num}",
                weekday,
                tb_display.get(block_code, block_code),
                dp.program_title or "" if dp else "",
                dp.summary_text or "" if dp else "",
            ]
            for staff in staff_list:
                a = assign_index.get((current_date, block_code, str(staff.id)))
                cell_text = ""
                if a:
                    parts = []
                    if a.task_type_code:
                        parts.append(a.task_type_code)
                    if a.display_text:
                        parts.append(a.display_text)
                    cell_text = " ".join(parts)
                row.append(cell_text)
            writer.writerow(row)

    return output.getvalue()
