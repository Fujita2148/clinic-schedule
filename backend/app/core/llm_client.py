"""Anthropic Claude API client wrapper for Tool Use."""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


async def call_tool_use(
    system: str,
    user_message: str,
    tools: list[dict],
    model: str = "claude-sonnet-4-5-20250929",
) -> dict | None:
    """Call Claude API with Tool Use and return the first tool_use block input.

    Returns None if ANTHROPIC_API_KEY is not configured or no tool call is made.
    """
    if not settings.ANTHROPIC_API_KEY:
        return None

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_message}],
            tools=tools,
        )

        for block in response.content:
            if block.type == "tool_use":
                return block.input

        logger.warning("Claude API returned no tool_use block")
        return None

    except Exception:
        logger.exception("Claude API call failed")
        raise
