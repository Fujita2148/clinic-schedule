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


class NlpParsedRule(BaseModel):
    natural_text: str
    template_type: str = "headcount"
    hard_or_soft: str = "soft"
    weight: int = 100
    body: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class NlpRuleParseResponse(BaseModel):
    parsed: NlpParsedRule


class NlpExplainRequest(BaseModel):
    schedule_id: str


class NlpExplainResponse(BaseModel):
    explanation: str
    num_violations: int
