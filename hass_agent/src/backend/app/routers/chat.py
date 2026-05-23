from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from openai.types import chat
from pydantic_ai import Agent
from pydantic_ai.messages import FunctionToolResultEvent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from app.agent import AgentDeps, agent
from app.config import settings
from app.db import (
    accumulate_token_usage,
    create_session,
    get_message_history,
    get_session,
    save_display_message,
    save_message_history,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def _to_json_str(content: object) -> str:
    """Serialize tool result content to a JSON string, falling back to str()."""
    if isinstance(content, str):
        try:
            # Already a JSON string? Round-trip to normalise (Python repr → real JSON)
            parsed = json.loads(content)
            return json.dumps(parsed, indent=2)
        except (json.JSONDecodeError, ValueError):
            pass
        # Try eval as Python literal (handles single-quote dicts from HA tools)
        try:
            import ast
            parsed = ast.literal_eval(content)
            return json.dumps(parsed, indent=2)
        except Exception:
            return content
    try:
        return json.dumps(content, indent=2)
    except Exception:
        return str(content)


class _OpenAICompatibleChatModel(OpenAIChatModel):
    """OpenAI-compatible model that avoids content=None for servers like llama.cpp."""

    @dataclass
    class _MapModelResponseContext(OpenAIChatModel._MapModelResponseContext):
        def _into_message_param(self) -> chat.ChatCompletionAssistantMessageParam:
            msg = super()._into_message_param()
            if msg.get("content") is None:
                msg["content"] = ""
            return msg



def _resolve_model(model_id: str):
    """Map a model ID string to a PydanticAI model."""
    if model_id.startswith("openai:"):
        model_name = model_id.removeprefix("openai:")
        base_url = f"{settings.openai_base_url.rstrip('/')}/v1"
        api_key = settings.openai_api_key or "not-needed"
        return _OpenAICompatibleChatModel(model_name, provider=OpenAIProvider(base_url=base_url, api_key=api_key))
    if model_id.startswith("google-gla:"):
        model_name = model_id.removeprefix("google-gla:")
        return GoogleModel(
            model_name=model_name,
            provider=GoogleProvider(api_key=settings.gemini_api_key),
        )
    # Fallback: use the model_id directly
    return model_id


@router.websocket("/ws/chat")
async def chat_ws(ws: WebSocket, session_id: str | None = None) -> None:
    # Check auth before accepting the WebSocket
    user = ws.session.get("user")
    if not user:
        await ws.close(code=4001, reason="Not authenticated")
        return

    await ws.accept()
    ha_client = ws.app.state.ha_client
    db = ws.app.state.db
    user_id: str = user["id"]

    # Load existing history if resuming a session
    if session_id:
        session = await get_session(db, session_id)
        if not session or session.get("user_id") != user_id:
            await ws.send_json({"type": "error", "content": "Session not found"})
            await ws.close()
            return
        message_history = await get_message_history(db, session_id)
    else:
        message_history = []

    try:
        while True:
            data = json.loads(await ws.receive_text())
            user_msg = data.get("message", "")
            model_id = data.get("model", f"google-gla:{settings.gemini_model}")

            # Auto-create session on first message
            if not session_id:
                title = user_msg[:80].strip() or "New chat"
                session = await create_session(db, title, user_id)
                session_id = session["id"]
                await ws.send_json({
                    "type": "session_created",
                    "session_id": session_id,
                    "title": title,
                })

            model = _resolve_model(model_id)
            deps = AgentDeps(ha=ha_client)

            # Track streamed content for display persistence
            assistant_content = ""
            tool_calls_display: list[dict] = []

            try:
                async with agent.iter(
                    user_msg,
                    deps=deps,
                    model=model,
                    message_history=message_history,
                ) as run:
                    async for node in run:
                        if Agent.is_model_request_node(node):
                            async with node.stream(run.ctx) as stream:
                                async for chunk in stream.stream_text(delta=True):
                                    assistant_content += chunk
                                    await ws.send_json({"type": "token", "content": chunk})

                        elif Agent.is_call_tools_node(node):
                            for part in node.model_response.parts:
                                if hasattr(part, "tool_name"):
                                    tc = {
                                        "name": part.tool_name,
                                        "args": part.args
                                        if isinstance(part.args, dict)
                                        else {},
                                    }
                                    tool_calls_display.append(tc)
                                    await ws.send_json({
                                        "type": "tool_call",
                                        "name": part.tool_name,
                                        "args": tc["args"],
                                    })
                            # Execute tools and report results
                            async with node.stream(run.ctx) as handle_stream:
                                async for event in handle_stream:
                                    if isinstance(event, FunctionToolResultEvent):
                                        result_str = _to_json_str(event.result.content)
                                        # Update matching tool call with result
                                        for tc in tool_calls_display:
                                            if tc["name"] == event.result.tool_name and "result" not in tc:
                                                tc["result"] = result_str
                                                break
                                        await ws.send_json({
                                            "type": "tool_result",
                                            "name": event.result.tool_name,
                                            "content": result_str,
                                        })

                    # Save conversation history for multi-turn
                    if run.result:
                        message_history = run.result.all_messages()

                    # Capture and persist token usage
                    run_usage = run.usage()
                    assert session_id is not None
                    totals = await accumulate_token_usage(
                        db,
                        session_id,
                        input_tokens=run_usage.input_tokens,
                        output_tokens=run_usage.output_tokens,
                        context_tokens=run_usage.input_tokens,
                    )
                    await ws.send_json({"type": "usage", **totals})

            except Exception as e:
                logger.exception("Agent run error")
                err_msg = f"\n\n**Error:** {e}"
                assistant_content += err_msg
                await ws.send_json({"type": "token", "content": err_msg})

            # Persist to database
            assert session_id is not None  # guaranteed set above
            await save_display_message(db, session_id, "user", user_msg)
            await save_display_message(
                db,
                session_id,
                "assistant",
                assistant_content,
                tool_calls_display if tool_calls_display else None,
            )
            await save_message_history(db, session_id, message_history)

            await ws.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.exception("Chat connection error")
        try:
            await ws.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
