"""Pydantic schemas for NLP (Claude API) parse requests/responses."""

from pydantic import BaseModel, Field


class NlpParseRequest(BaseModel):
    text: str
    schedule_id: str | None = None


class NlpTimeConstraint(BaseModel):
    type: str  # fixed | range | candidates
    data: dict = Field(default_factory=dict)


class NlpParsedEvent(BaseModel):
    type_code: str | None = None
    subject_name: str | None = None
    location_type: str = "in_clinic"
    duration_hours: int = 1
    time_constraint: NlpTimeConstraint = Field(
        default_factory=lambda: NlpTimeConstraint(type="fixed", data={})
    )
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_resources: list[str] = Field(default_factory=list)
    priority: str = "required"
    deadline: str | None = None
    notes: str | None = None


class NlpParseResponse(BaseModel):
    parsed: NlpParsedEvent
    confidence: str | None = None
    clarification: str | None = None
