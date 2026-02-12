"""Solver API — auto-schedule generation using OR-Tools CP-SAT."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schedule import Schedule
from app.schemas.solver import MultiSolveRequest, MultiSolveResponse, SolutionSummary, SolveRequest, SolveResponse, SolveStats
from app.services.solver_service import apply_solver_result, solve_schedule, solve_schedule_multi

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


@router.post("/solutions", response_model=MultiSolveResponse)
async def run_multi_solver(
    schedule_id: uuid.UUID,
    request: MultiSolveRequest = MultiSolveRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Generate 3 solution variants (A/B/C) with different optimization presets."""
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.status == "confirmed":
        raise HTTPException(status_code=403, detail="確定済みスケジュールは変更できません")

    results = await solve_schedule_multi(
        db, schedule, time_limit_seconds=request.time_limit_seconds
    )

    if not results:
        return MultiSolveResponse(
            solutions=[],
            message="職員が登録されていないため、案を生成できません。",
        )

    # Store solution data on schedule for later retrieval
    schedule.solver_result = {
        "multi_solutions": [
            {
                "preset": r["preset"],
                "label": r["label"],
                "status": r["status"],
                "num_assignments": r["num_assignments"],
                "num_events_placed": r["num_events_placed"],
                "objective_value": r["objective_value"],
            }
            for r in results
        ],
        "solutions_data": {
            r["preset"]: r["assignments"] for r in results
        },
    }
    await db.flush()

    summaries = [
        SolutionSummary(
            preset=r["preset"],
            label=r["label"],
            status=r["status"],
            objective_value=r["objective_value"],
            num_assignments=r["num_assignments"],
            num_events_placed=r["num_events_placed"],
            stats=SolveStats(**r["stats"]),
        )
        for r in results
    ]

    feasible_count = sum(1 for s in summaries if s.status in ("OPTIMAL", "FEASIBLE"))
    message = f"{feasible_count}/3 の案が生成されました。"

    return MultiSolveResponse(solutions=summaries, message=message)


@router.post("/solutions/{preset}/apply")
async def apply_solution(
    schedule_id: uuid.UUID,
    preset: str,
    db: AsyncSession = Depends(get_db),
):
    """Apply a specific solution preset (A/B/C) to the schedule."""
    schedule = await db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.status == "confirmed":
        raise HTTPException(status_code=403, detail="確定済みスケジュールは変更できません")

    preset = preset.upper()
    if preset not in ("A", "B", "C"):
        raise HTTPException(status_code=400, detail="preset must be A, B, or C")

    solver_result = schedule.solver_result or {}
    solutions_data = solver_result.get("solutions_data", {})
    assignments = solutions_data.get(preset)

    if assignments is None:
        raise HTTPException(
            status_code=404,
            detail=f"案{preset}のデータが見つかりません。先に /solve/solutions を実行してください。",
        )

    num = await apply_solver_result(db, schedule_id, assignments, clear_unlocked=True)
    await db.flush()

    return {
        "status": "applied",
        "preset": preset,
        "num_assignments": num,
        "message": f"案{preset}を適用しました。{num}件の割当を生成しました。",
    }
