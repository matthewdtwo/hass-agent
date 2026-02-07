from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic_ai import Agent
from pydantic_ai.messages import FunctionToolResultEvent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.ollama import OllamaProvider

from app.agent import AgentDeps, agent
from app.config import settings
from app.db import (
    create_session,
    get_message_history,
    get_session,
    save_display_message,
    save_message_history,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def _resolve_model(model_id: str):
    """Map a model ID string to a PydanticAI model."""
    if model_id.startswith("ollama:"):
        model_name = model_id.removeprefix("ollama:")
        return OpenAIChatModel(model_name, provider=OllamaProvider(base_url=f"{settings.ollama_host}/v1"))
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
                                        result_str = str(event.result.content)[:500]
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
