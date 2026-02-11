from pydantic import BaseModel


class TimeBlockResponse(BaseModel):
    code: str
    display_name: str
    start_time: str
    end_time: str
    duration_minutes: int
    sort_order: int

    model_config = {"from_attributes": True}


class ColorLegendBase(BaseModel):
    code: str
    display_name: str
    bg_color: str
    text_color: str = "#000000"
    hatch_pattern: str | None = None
    icon: str | None = None
    sort_order: int
    is_system: bool = False
    is_active: bool = True


class ColorLegendUpdate(BaseModel):
    display_name: str | None = None
    bg_color: str | None = None
    text_color: str | None = None
    hatch_pattern: str | None = None
    icon: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class ColorLegendResponse(ColorLegendBase):
    model_config = {"from_attributes": True}
