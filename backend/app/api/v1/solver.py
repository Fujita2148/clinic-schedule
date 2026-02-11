"""Solver API — auto-schedule generation using OR-Tools CP-SAT."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schedule import Schedule
from app.schemas.solver import SolveRequest, SolveResponse, SolveStats
from app.services.solver_service import apply_solver_result, solve_schedule

router = APIRouter(prefix="/schedules/{schedule_id}/solve", tags=["solver"])


@router.post("", response_model=SolveResponse)
async def run_solver(
    schedule_id: uuid.UUID,
    request: SolveRequest = SolveRequest(),
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.status == "confirmed":
        raise HTTPException(status_code=403, detail="確定済みスケジュールは変更できません")

    # Run solver
    result = await solve_schedule(db, schedule, time_limit_seconds=request.time_limit_seconds)

    status = result["status"]
    assignments = result["assignments"]
    stats = result["stats"]

    if status in ("OPTIMAL", "FEASIBLE"):
        # Apply assignments
        num = await apply_solver_result(
            db, schedule_id, assignments, clear_unlocked=request.clear_unlocked
        )
        # Store solver metadata
        schedule.solver_result = stats
        await db.flush()

        message = f"{'最適解' if status == 'OPTIMAL' else '実行可能解'}が見つかりました。{num}件の割当を生成しました。"
    elif status == "INFEASIBLE":
        num = 0
        message = "制約を満たす解が見つかりませんでした。ルールやロック済み割当を見直してください。"
    else:
        num = 0
        message = f"ソルバーのステータス: {status}"

    return SolveResponse(
        status=status,
        num_assignments=num,
        stats=SolveStats(**stats),
        message=message,
    )
