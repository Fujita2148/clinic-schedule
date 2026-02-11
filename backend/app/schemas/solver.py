"""Pydantic schemas for solver API."""

from pydantic import BaseModel


class SolveRequest(BaseModel):
    time_limit_seconds: int = 30
    clear_unlocked: bool = True


class SolveStats(BaseModel):
    status: str
    objective_value: float | None = None
    wall_time: float | None = None
    num_assignments_generated: int = 0
    num_staff: int = 0
    num_dates: int = 0


class SolveResponse(BaseModel):
    status: str
    num_assignments: int
    stats: SolveStats
    message: str
