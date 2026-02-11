from pydantic import BaseModel


class TaskTypeBase(BaseModel):
    code: str
    display_name: str
    default_blocks: list[str] = ["am"]
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    required_resources: list[str] = []
    min_staff: int = 1
    max_staff: int | None = None
    tags: list[str] = []
    location_type: str = "in_clinic"
    is_active: bool = True


class TaskTypeCreate(TaskTypeBase):
    pass


class TaskTypeUpdate(BaseModel):
    display_name: str | None = None
    default_blocks: list[str] | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    required_resources: list[str] | None = None
    min_staff: int | None = None
    max_staff: int | None = None
    tags: list[str] | None = None
    location_type: str | None = None
    is_active: bool | None = None


class TaskTypeResponse(TaskTypeBase):
    model_config = {"from_attributes": True}
