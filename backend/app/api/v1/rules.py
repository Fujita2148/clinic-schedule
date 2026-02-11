"""Rules API — CRUD for scheduling constraints/rules."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rule import Rule
from app.schemas.rule import RuleCreate, RuleResponse, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    is_active: bool | None = None,
    template_type: str | None = None,
    hard_or_soft: str | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Rule).order_by(Rule.created_at.desc())
    if is_active is not None:
        query = query.where(Rule.is_active == is_active)
    if template_type:
        query = query.where(Rule.template_type == template_type)
    if hard_or_soft:
        query = query.where(Rule.hard_or_soft == hard_or_soft)
    result = await db.execute(query)
    rules = result.scalars().all()

    # Filter by tag if specified (JSON array contains)
    if tag:
        rules = [r for r in rules if tag in (r.tags or [])]

    return rules


@router.post("", response_model=RuleResponse, status_code=201)
async def create_rule(
    data: RuleCreate,
    db: AsyncSession = Depends(get_db),
):
    rule = Rule(**data.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="ルールが見つかりません")
    return rule


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    data: RuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="ルールが見つかりません")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)

    await db.flush()
    await db.refresh(rule)
    return rule


@router.patch("/{rule_id}/toggle", response_model=RuleResponse)
async def toggle_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="ルールが見つかりません")

    rule.is_active = not rule.is_active
    await db.flush()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="ルールが見つかりません")

    await db.delete(rule)
