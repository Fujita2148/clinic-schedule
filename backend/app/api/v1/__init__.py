from fastapi import APIRouter

from app.api.v1.assignments import router as assignments_router
from app.api.v1.color_legend import router as color_legend_router
from app.api.v1.day_programs import router as day_programs_router
from app.api.v1.export import router as export_router
from app.api.v1.grid import router as grid_router
from app.api.v1.resources import router as resources_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.staffs import router as staffs_router
from app.api.v1.task_types import router as task_types_router
from app.api.v1.time_blocks import router as time_blocks_router
from app.api.v1.violations import router as violations_router

router = APIRouter()
router.include_router(staffs_router)
router.include_router(task_types_router)
router.include_router(schedules_router)
router.include_router(assignments_router)
router.include_router(grid_router)
router.include_router(color_legend_router)
router.include_router(time_blocks_router)
router.include_router(day_programs_router)
router.include_router(resources_router)
router.include_router(export_router)
router.include_router(violations_router)
