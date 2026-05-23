from __future__ import annotations

import logging
from datetime import datetime, timezone

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

logger = logging.getLogger(__name__)

_summarizer: Agent[None, str] = Agent(
    system_prompt=(
        "You are a concise summarizer. Given a conversation transcript, produce "
        "a dense summary that preserves all key facts, decisions, entity IDs, "
        "states, and context needed to continue the conversation. "
        "Focus on technical details. Be thorough but compact."
    ),
)


def _estimate_tokens(messages: list[ModelMessage]) -> int:
    """Conservative token estimate: 1 token ≈ 3 characters (accounts for code/JSON density)."""
    total = 0
    for msg in messages:
        for part in msg.parts:
            content = getattr(part, "content", None)
            if content is not None:
                total += len(content if isinstance(content, str) else str(content))
            args = getattr(part, "args", None)
            if args is not None:
                total += len(str(args))
    return total // 3


# Tokens reserved for system prompt + tool definitions + current user message.
# This headroom is NOT in message_history but IS counted by the model.
_SYSTEM_OVERHEAD_TOKENS = 4096


def _messages_to_transcript(messages: list[ModelMessage]) -> str:
    """Convert messages to a readable transcript for summarization."""
    lines = []
    for msg in messages:
        role = "User" if isinstance(msg, ModelRequest) else "Assistant"
        for part in msg.parts:
            content = getattr(part, "content", None)
            if isinstance(content, str) and content.strip():
                lines.append(f"{role}: {content}")
            tool_name = getattr(part, "tool_name", None)
            if tool_name:
                args = getattr(part, "args", "")
                lines.append(f"[Tool call: {tool_name}({args})]")
    return "\n".join(lines)


async def manage_context(
    messages: list[ModelMessage],
    max_tokens: int,
    model: object,
) -> tuple[list[ModelMessage], str | None]:
    """
    Returns ``(managed_messages, summary_text | None)``.
    ``summary_text`` is set when old messages were replaced with a summary.
    """
    """
    Sliding window + summarization context management.

    - If estimated tokens ≤ 85% of max_tokens: return unchanged.
    - Otherwise: keep the most recent messages fitting in 60% of the budget
      (sliding window), summarize the older remainder, and prepend a synthetic
      summary exchange so the model has the earlier context.
    """
    if not messages:
        return messages, None

    total = _estimate_tokens(messages)
    # Effective token budget for message history: subtract fixed overhead for
    # system prompt + tool definitions + current user message.
    history_budget = max(max_tokens - _SYSTEM_OVERHEAD_TOKENS, max_tokens // 2)
    threshold = int(history_budget * 0.85)

    if total <= threshold:
        return messages, None

    logger.info(
        "Context limit approaching (~%d tokens estimated, threshold %d / history budget %d); "
        "applying sliding window + summarization",
        total,
        threshold,
        history_budget,
    )

    # Walk newest → oldest, accumulate until 60% of history budget is filled
    recent_budget_chars = int(history_budget * 0.60) * 3
    recent: list[ModelMessage] = []
    recent_chars = 0
    cutoff = len(messages)

    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        msg_chars = sum(
            len(getattr(part, "content", "") or "")
            for part in msg.parts
            if isinstance(getattr(part, "content", None), str)
        )
        if recent_chars + msg_chars > recent_budget_chars:
            cutoff = i + 1
            break
        recent.insert(0, msg)
        recent_chars += msg_chars
    else:
        cutoff = 0

    old_messages = messages[:cutoff]
    if not old_messages:
        return recent, None

    transcript = _messages_to_transcript(old_messages)
    logger.info(
        "Summarizing %d old messages (%d chars) to free context",
        len(old_messages),
        len(transcript),
    )

    try:
        result = await _summarizer.run(
            f"Please summarize this conversation:\n\n{transcript}",
            model=model,
        )
        summary_text = result.data
        logger.info("Summary generated (%d chars)", len(summary_text))
    except Exception as exc:
        logger.warning(
            "Summarization failed (%s: %s); falling back to sliding window only",
            type(exc).__name__,
            exc,
        )
        return recent, None

    now = datetime.now(timezone.utc)
    summary_exchange: list[ModelMessage] = [
        ModelRequest(
            parts=[
                UserPromptPart(
                    content=(
                        "[Context: The following is a summary of our earlier conversation. "
                        "Use it as background context to continue.]\n\n" + summary_text
                    ),
                    timestamp=now,
                )
            ]
        ),
        ModelResponse(
            parts=[TextPart(content="Understood, I have the context from our earlier conversation.")],
            model_name="context-manager",
            timestamp=now,
        ),
    ]

    return summary_exchange + recent, summary_text
