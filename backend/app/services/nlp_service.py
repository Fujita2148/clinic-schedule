"""NLP service — parse natural language into structured events via Claude API."""

from fastapi import HTTPException

from app.core.llm_client import call_tool_use
from app.schemas.nlp import NlpParsedEvent, NlpTimeConstraint

# Claude Tool Use tool definition for create_event (DESIGN.md §5.1)
CREATE_EVENT_TOOL = {
    "name": "create_event",
    "description": "自然文からイベント(予定・案件)を構造化して作成する",
    "input_schema": {
        "type": "object",
        "properties": {
            "type_code": {
                "type": "string",
                "description": "業務コード (task_types テーブルの code)",
            },
            "subject_name": {
                "type": "string",
                "description": "患者名/プログラム名",
            },
            "location_type": {
                "type": "string",
                "enum": ["in_clinic", "outing", "visit"],
                "description": "場所種別: in_clinic=院内, outing=外出, visit=訪問",
            },
            "duration_hours": {
                "type": "integer",
                "minimum": 1,
                "description": "所要時間(時間単位)",
            },
            "time_constraint": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["fixed", "range", "candidates"],
                        "description": "fixed=日時確定, range=範囲指定, candidates=候補日時",
                    },
                    "data": {
                        "type": "object",
                        "description": "fixed: {date,start} / range: {weekdays,period,month} / candidates: {slots:[{date,start},...]}",
                    },
                },
                "required": ["type", "data"],
            },
            "required_skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "必須スキルコード (例: CP, PSW, NS)",
            },
            "preferred_skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "優先スキルコード",
            },
            "required_resources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "必要リソース (例: car, room)",
            },
            "priority": {
                "type": "string",
                "enum": ["required", "high", "medium", "low"],
                "description": "優先度",
            },
            "deadline": {
                "type": "string",
                "format": "date",
                "description": "期限 (YYYY-MM-DD)",
            },
            "notes": {
                "type": "string",
                "description": "備考",
            },
        },
        "required": ["location_type", "duration_hours", "time_constraint"],
    },
}


def _build_system_prompt(task_types: list[dict], rules: list[dict]) -> str:
    """Build the system prompt including business code dictionary and rules."""
    task_type_lines = "\n".join(
        f"- {tt['code']}: {tt['display_name']} (場所: {tt.get('location_type', '?')}, "
        f"必須スキル: {tt.get('required_skills', [])})"
        for tt in task_types
    )

    rule_lines = "\n".join(
        f"- {r.get('natural_text', '(不明)')}" for r in rules[:20]
    )

    return f"""あなたはクリニックのスケジュール管理AIアシスタントです。
ユーザーの自然文入力を解析し、create_event ツールを使ってイベント(予定)を構造化してください。

## 業務コード辞書
{task_type_lines or "(未登録)"}

## 現在のルール
{rule_lines or "(未登録)"}

## 注意事項
- type_code は業務コード辞書に存在するコードのみ使用してください。該当がなければ省略してください。
- 時間の候補が明示されていない場合は range タイプで推定してください。
- weekdays は 0=月, 1=火, 2=水, 3=木, 4=金, 5=土, 6=日 です。
- period は "am" (午前) または "pm" (午後) です。
- 必ず create_event ツールを呼び出してください。"""


async def parse_event_from_text(
    text: str,
    task_types: list[dict],
    rules: list[dict],
) -> NlpParsedEvent:
    """Parse natural language text into a structured event using Claude API."""
    system_prompt = _build_system_prompt(task_types, rules)

    result = await call_tool_use(
        system=system_prompt,
        user_message=text,
        tools=[CREATE_EVENT_TOOL],
    )

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY が設定されていないか、Claude API が応答しませんでした",
        )

    # Map the tool call result to NlpParsedEvent
    tc = result.get("time_constraint", {})
    return NlpParsedEvent(
        type_code=result.get("type_code"),
        subject_name=result.get("subject_name"),
        location_type=result.get("location_type", "in_clinic"),
        duration_hours=result.get("duration_hours", 1),
        time_constraint=NlpTimeConstraint(
            type=tc.get("type", "fixed"),
            data=tc.get("data", {}),
        ),
        required_skills=result.get("required_skills", []),
        preferred_skills=result.get("preferred_skills", []),
        required_resources=result.get("required_resources", []),
        priority=result.get("priority", "required"),
        deadline=result.get("deadline"),
        notes=result.get("notes"),
    )
