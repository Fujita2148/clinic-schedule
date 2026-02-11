"""Database initialization and seed data."""

from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Base
from app.models.master import ColorLegend, TimeBlockMaster
from app.models.rule import Rule
from app.models.staff import SkillMaster, Staff
from app.models.task_type import TaskType
from app.core.database import engine


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_time_blocks(db: AsyncSession):
    existing = await db.execute(select(TimeBlockMaster))
    if existing.scalars().first():
        return

    blocks = [
        TimeBlockMaster(code="am", display_name="AM", start_time=time(9, 0), end_time=time(12, 0), duration_minutes=180, sort_order=1),
        TimeBlockMaster(code="lunch", display_name="昼", start_time=time(12, 0), end_time=time(13, 0), duration_minutes=60, sort_order=2),
        TimeBlockMaster(code="pm", display_name="PM", start_time=time(13, 0), end_time=time(15, 0), duration_minutes=120, sort_order=3),
        TimeBlockMaster(code="15", display_name="15時", start_time=time(15, 0), end_time=time(16, 0), duration_minutes=60, sort_order=4),
        TimeBlockMaster(code="16", display_name="16時", start_time=time(16, 0), end_time=time(17, 0), duration_minutes=60, sort_order=5),
        TimeBlockMaster(code="17", display_name="17時", start_time=time(17, 0), end_time=time(18, 0), duration_minutes=60, sort_order=6),
        TimeBlockMaster(code="18plus", display_name="18-", start_time=time(18, 0), end_time=time(20, 0), duration_minutes=120, sort_order=7),
    ]
    db.add_all(blocks)


async def seed_color_legend(db: AsyncSession):
    existing = await db.execute(select(ColorLegend))
    if existing.scalars().first():
        return

    colors = [
        ColorLegend(code="off", display_name="休み", bg_color="#FF0000", text_color="#FFFFFF", hatch_pattern="diagonal", sort_order=1, is_system=True),
        ColorLegend(code="pre_work", display_name="出勤前", bg_color="#FFB6C1", text_color="#000000", sort_order=2, is_system=True),
        ColorLegend(code="post_work", display_name="退勤後", bg_color="#800080", text_color="#FFFFFF", sort_order=3, is_system=True),
        ColorLegend(code="visit", display_name="訪問", bg_color="#008000", text_color="#FFFFFF", icon="🚲", sort_order=4, is_system=True),
    ]
    db.add_all(colors)


async def seed_skills(db: AsyncSession):
    existing = await db.execute(select(SkillMaster))
    if existing.scalars().first():
        return

    skills = [
        SkillMaster(code="PSW", name="精神保健福祉士", description="PSW資格"),
        SkillMaster(code="CP", name="臨床心理士", description="心理検査・面接対応"),
        SkillMaster(code="NURSE", name="看護師", description="訪問看護対応"),
        SkillMaster(code="DRIVER", name="運転免許", description="車での訪問対応"),
        SkillMaster(code="OT", name="作業療法士"),
        SkillMaster(code="DOCTOR", name="医師"),
    ]
    db.add_all(skills)


async def seed_task_types(db: AsyncSession):
    existing = await db.execute(select(TaskType))
    if existing.scalars().first():
        return

    task_types = [
        TaskType(code="daycare", display_name="デイケア", default_blocks=["am", "pm"], min_staff=2, tags=["デイケア"], location_type="in_clinic"),
        TaskType(code="nightcare", display_name="ナイトケア", default_blocks=["16", "17", "18plus"], min_staff=2, tags=["ナイトケア"], location_type="in_clinic"),
        TaskType(code="visit_nurse", display_name="訪問看護", default_blocks=["am"], required_skills=["NURSE"], required_resources=["bicycle"], tags=["訪問"], location_type="visit"),
        TaskType(code="interview", display_name="面接", default_blocks=["am"], required_skills=["CP"], tags=["面接"], location_type="in_clinic"),
        TaskType(code="psych_test", display_name="心理検査", default_blocks=["pm"], required_skills=["CP"], required_resources=["room"], tags=["検査"], location_type="in_clinic"),
        TaskType(code="meeting", display_name="会議", default_blocks=["16"], tags=["会議"], location_type="in_clinic"),
        TaskType(code="office_work", display_name="事務", default_blocks=["am"], tags=["事務"], location_type="in_clinic"),
        TaskType(code="outing", display_name="外出プログラム", default_blocks=["am", "pm"], min_staff=3, tags=["外出"], location_type="outing"),
        TaskType(code="off", display_name="休み", default_blocks=["am", "lunch", "pm", "15", "16", "17", "18plus"], tags=["休み"]),
        TaskType(code="nc_prep", display_name="NC準備", default_blocks=["15"], tags=["ナイトケア"], location_type="in_clinic"),
    ]
    db.add_all(task_types)


async def seed_sample_staff(db: AsyncSession):
    existing = await db.execute(select(Staff))
    if existing.scalars().first():
        return

    staffs = [
        Staff(name="藤田", employment_type="full_time", job_category="PSW", can_drive=True, can_bicycle=True),
        Staff(name="小石", employment_type="full_time", job_category="CP", can_drive=False, can_bicycle=True),
        Staff(name="三田村", employment_type="full_time", job_category="PSW", can_drive=True, can_bicycle=True),
        Staff(name="高松", employment_type="full_time", job_category="事務", can_drive=False, can_bicycle=True),
        Staff(name="岩野", employment_type="full_time", job_category="PSW", can_drive=True, can_bicycle=True),
        Staff(name="森井", employment_type="full_time", job_category="CP", can_drive=False, can_bicycle=True),
        Staff(name="八木", employment_type="part_time", job_category="看護師", can_drive=False, can_bicycle=True),
        Staff(name="安藤", employment_type="full_time", job_category="PSW", can_drive=True, can_bicycle=True),
    ]
    db.add_all(staffs)


async def seed_rules(db: AsyncSession):
    existing = await db.execute(select(Rule))
    if existing.scalars().first():
        return

    rules = [
        Rule(
            natural_text="外出プログラムの時は職員3人つくこと",
            template_type="headcount",
            scope={"type": "task_type"},
            hard_or_soft="hard",
            weight=1000,
            body={"task_type_code": "outing", "min_staff": 3},
            tags=["外出", "人員配置"],
            applies_to={"task_type": "outing"},
        ),
        Rule(
            natural_text="デイケアは最低2名体制",
            template_type="headcount",
            scope={"type": "task_type"},
            hard_or_soft="soft",
            weight=800,
            body={"task_type_code": "daycare", "min_staff": 2},
            tags=["デイケア", "人員配置"],
            applies_to={"task_type": "daycare"},
        ),
        Rule(
            natural_text="ナイトケアは最低2名体制",
            template_type="headcount",
            scope={"type": "task_type"},
            hard_or_soft="soft",
            weight=800,
            body={"task_type_code": "nightcare", "min_staff": 2},
            tags=["ナイトケア", "人員配置"],
            applies_to={"task_type": "nightcare"},
        ),
        Rule(
            natural_text="八木さんは金曜午後勤務不可",
            template_type="availability",
            scope={"type": "weekly", "weekday": 4},
            hard_or_soft="soft",
            weight=600,
            body={"staff_name": "八木", "blocked_weekdays": [4], "blocked_blocks": ["pm", "15", "16", "17", "18plus"]},
            tags=["勤務制限"],
        ),
        Rule(
            natural_text="訪問看護にはNURSEスキルが必要",
            template_type="skill_req",
            scope={"type": "task_type"},
            hard_or_soft="hard",
            weight=1000,
            body={"task_type_code": "visit_nurse", "required_skills": ["NURSE"]},
            tags=["スキル要件", "訪問"],
            applies_to={"task_type": "visit_nurse"},
        ),
        Rule(
            natural_text="心理検査にはCPスキルが必要",
            template_type="skill_req",
            scope={"type": "task_type"},
            hard_or_soft="hard",
            weight=1000,
            body={"task_type_code": "psych_test", "required_skills": ["CP"]},
            tags=["スキル要件", "検査"],
            applies_to={"task_type": "psych_test"},
        ),
    ]
    db.add_all(rules)


async def seed_all(db: AsyncSession):
    await seed_time_blocks(db)
    await seed_color_legend(db)
    await seed_skills(db)
    await seed_task_types(db)
    await seed_sample_staff(db)
    await seed_rules(db)
    await db.commit()
