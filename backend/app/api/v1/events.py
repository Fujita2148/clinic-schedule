"""Events API — CRUD for scheduling events + NLP parse."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.event import Event
from app.models.rule import Rule
from app.models.task_type import TaskType
from app.schemas.event import EventCreate, EventResponse, EventUpdate
from app.schemas.nlp import NlpParseRequest, NlpParseResponse
from app.services.nlp_service import parse_event_from_text

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventResponse])
async def list_events(
    status: str | None = None,
    schedule_id: str | None = None,
    type_code: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Event).order_by(Event.created_at.desc())
    if status:
        query = query.where(Event.status == status)
    if schedule_id:
        query = query.where(Event.schedule_id == uuid.UUID(schedule_id))
    if type_code:
        query = query.where(Event.type_code == type_code)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
):
    event_data = data.model_dump()
    # Auto-generate anonymous ID when subject_name is provided
    if event_data.get("subject_name"):
        event_data["subject_anonymous_id"] = f"ANON-{uuid.uuid4().hex[:8]}"
    event = Event(**event_data)
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@router.post("/from-text", response_model=NlpParseResponse)
async def parse_event_text(
    data: NlpParseRequest,
    db: AsyncSession = Depends(get_db),
):
    """Parse natural language text into a structured event using Claude API."""
    # Fetch task_types and active rules for context
    tt_result = await db.execute(
        select(TaskType).where(TaskType.is_active.is_(True))
    )
    task_types = [
        {
            "code": tt.code,
            "display_name": tt.display_name,
            "location_type": tt.location_type,
            "required_skills": tt.required_skills,
        }
        for tt in tt_result.scalars().all()
    ]

    rule_result = await db.execute(
        select(Rule).where(Rule.is_active.is_(True)).limit(20)
    )
    rules = [
        {"natural_text": r.natural_text, "template_type": r.template_type}
        for r in rule_result.scalars().all()
    ]

    parsed = await parse_event_from_text(
        text=data.text,
        task_types=task_types,
        rules=rules,
    )

    return NlpParseResponse(parsed=parsed)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")
    return event


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: uuid.UUID,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")

    update_data = data.model_dump(exclude_unset=True)
    # Regenerate anonymous ID if subject_name changes
    if "subject_name" in update_data and update_data["subject_name"]:
        if not event.subject_anonymous_id:
            update_data["subject_anonymous_id"] = f"ANON-{uuid.uuid4().hex[:8]}"
    for key, value in update_data.items():
        setattr(event, key, value)

    await db.flush()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")
    await db.delete(event)
