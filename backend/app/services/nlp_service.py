"""NLP service — parse natural language into structured events/rules via Claude API."""

from fastapi import HTTPException

from app.core.llm_client import call_text, call_tool_use
from app.schemas.nlp import NlpParsedEvent, NlpParsedRule, NlpTimeConstraint

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

# Claude Tool Use tool definition for create_rule
CREATE_RULE_TOOL = {
    "name": "create_rule",
    "description": "自然文からスケジューリングルール(制約)を構造化して作成する",
    "input_schema": {
        "type": "object",
        "properties": {
            "natural_text": {
                "type": "string",
                "description": "ルールの自然文表現（元の入力をそのまま、または少し整形して）",
            },
            "template_type": {
                "type": "string",
                "enum": ["headcount", "availability", "skill_req", "resource_req", "preference", "recurring", "specific_date"],
                "description": "headcount=人員配置, availability=勤務制限, skill_req=スキル要件, resource_req=リソース要件, preference=優先配置, recurring=定期予定, specific_date=特定日",
            },
            "hard_or_soft": {
                "type": "string",
                "enum": ["hard", "soft"],
                "description": "hard=必須制約, soft=推奨制約（違反にペナルティ）",
            },
            "weight": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
                "description": "soft制約の場合の重み (1-1000)。hardの場合は1000を指定。",
            },
            "body": {
                "type": "object",
                "description": "ルールの詳細パラメータ。template_typeに応じて異なる構造。headcount: {task_type_code, min_staff, max_staff}, availability: {staff_name, blocked_weekdays[], blocked_blocks[]}, preference: {preferred_staff_name, task_type_code, weekday}, recurring: {weekdays[], task_type_code, min_staff, time_blocks[]}, specific_date: {date, task_type_code, min_staff, required_staff_names[], time_block}",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "タグ（カテゴリ分類用）",
            },
        },
        "required": ["natural_text", "template_type", "hard_or_soft", "weight", "body"],
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


def _build_rule_system_prompt(
    task_types: list[dict],
    staff_names: list[str],
    existing_rules: list[dict],
) -> str:
    """Build the system prompt for rule parsing."""
    task_type_lines = "\n".join(
        f"- {tt['code']}: {tt['display_name']}"
        for tt in task_types
    )

    staff_lines = ", ".join(staff_names[:30]) if staff_names else "(未登録)"

    existing_lines = "\n".join(
        f"- [{r.get('template_type', '?')}] {r.get('natural_text', '(不明)')}"
        for r in existing_rules[:20]
    )

    return f"""あなたはクリニックのスケジュール管理AIアシスタントです。
ユーザーの自然文入力を解析し、create_rule ツールを使ってスケジューリングルール(制約)を構造化してください。

## 業務コード辞書
{task_type_lines or "(未登録)"}

## 登録済み職員名
{staff_lines}

## 既存ルール
{existing_lines or "(なし)"}

## template_type ごとの body 構造
- headcount: {{"task_type_code": "dc", "min_staff": 2, "max_staff": 5}}
- availability: {{"staff_name": "山田", "blocked_weekdays": [2, 4], "blocked_blocks": ["pm"]}}
- preference: {{"preferred_staff_name": "山田", "task_type_code": "dc", "weekday": 3}}
- recurring: {{"weekdays": [0,1,2,3,4], "task_type_code": "dc", "min_staff": 2, "time_blocks": ["am", "pm"]}}
- specific_date: {{"date": "2025-05-15", "task_type_code": "dc", "min_staff": 3, "required_staff_names": ["山田"], "time_block": "pm"}}
- skill_req: {{"task_type_code": "psych_test", "required_skills": ["CP"]}}
- resource_req: {{"task_type_code": "visit_home", "required_resources": ["car"]}}

## 注意事項
- weekdays は 0=月, 1=火, 2=水, 3=木, 4=金, 5=土, 6=日 です。
- time_blocks / blocked_blocks には "am", "lunch", "pm", "15", "16", "17", "18plus" が使えます。
- task_type_code は業務コード辞書に存在するコードのみ使用してください。
- staff_name / required_staff_names / preferred_staff_name は登録済み職員名リストから選んでください。
- 制約の重要度に応じて hard/soft を選び、softの場合は適切なweightを設定してください。
- 必ず create_rule ツールを呼び出してください。"""


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


async def parse_rule_from_text(
    text: str,
    task_types: list[dict],
    staff_names: list[str],
    existing_rules: list[dict],
) -> NlpParsedRule:
    """Parse natural language text into a structured rule using Claude API."""
    system_prompt = _build_rule_system_prompt(task_types, staff_names, existing_rules)

    result = await call_tool_use(
        system=system_prompt,
        user_message=text,
        tools=[CREATE_RULE_TOOL],
    )

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY が設定されていないか、Claude API が応答しませんでした",
        )

    return NlpParsedRule(
        natural_text=result.get("natural_text", text),
        template_type=result.get("template_type", "headcount"),
        hard_or_soft=result.get("hard_or_soft", "soft"),
        weight=result.get("weight", 100),
        body=result.get("body", {}),
        tags=result.get("tags", []),
    )


async def explain_violations(
    violations: list[dict],
    schedule_year_month: str,
) -> str:
    """Generate a natural language explanation of schedule violations."""
    if not violations:
        return "違反はありません。スケジュールは全ての制約を満たしています。"

    violation_lines = []
    for i, v in enumerate(violations[:20], 1):
        line = f"{i}. [{v.get('violation_type', '?')}] {v.get('description', '?')}"
        if v.get("affected_date"):
            line += f" ({v['affected_date']}"
            if v.get("affected_time_block"):
                line += f" {v['affected_time_block']}"
            line += ")"
        if v.get("suggestion"):
            line += f" → 提案: {v['suggestion']}"
        violation_lines.append(line)

    user_message = f"""以下は {schedule_year_month} のスケジュールで検出された違反一覧です:

{chr(10).join(violation_lines)}

上記の違反をまとめて分析し、以下の点について日本語で簡潔に説明してください:
1. 全体の状況サマリー（1-2文）
2. 最も重要な問題とその影響
3. 具体的な改善提案（優先順に）"""

    system_prompt = """あなたはクリニックのスケジュール管理AIアシスタントです。
スケジュールの違反一覧を分析し、管理者にわかりやすく説明してください。
簡潔に、実用的なアドバイスを含めてください。マークダウンは使わず、プレーンテキストで回答してください。"""

    result = await call_text(
        system=system_prompt,
        user_message=user_message,
    )

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY が設定されていないか、Claude API が応答しませんでした",
        )

    return result
