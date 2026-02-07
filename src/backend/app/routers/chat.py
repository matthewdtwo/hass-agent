from __future__ import annotations

import asyncio
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
async def chat_ws(ws: WebSocket) -> None:
    await ws.accept()
    ha_client = ws.app.state.ha_client
    message_history: list = []

    try:
        while True:
            data = json.loads(await ws.receive_text())
            user_msg = data.get("message", "")
            model_id = data.get("model", f"google-gla:{settings.gemini_model}")

            model = _resolve_model(model_id)
            deps = AgentDeps(ha=ha_client)

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
                                await ws.send_json({"type": "token", "content": chunk})

                    elif Agent.is_call_tools_node(node):
                        for part in node.model_response.parts:
                            if hasattr(part, "tool_name"):
                                await ws.send_json({
                                    "type": "tool_call",
                                    "name": part.tool_name,
                                    "args": part.args
                                    if isinstance(part.args, dict)
                                    else {},
                                })
                        # Execute tools and report results
                        async with node.stream(run.ctx) as handle_stream:
                            async for event in handle_stream:
                                if isinstance(event, FunctionToolResultEvent):
                                    await ws.send_json({
                                        "type": "tool_result",
                                        "name": event.result.tool_name,
                                        "content": str(
                                            event.result.content
                                        )[:500],
                                    })

            # Save conversation history for multi-turn
            message_history = run.result.all_messages()
            await ws.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except asyncio.TimeoutError:
        logger.warning("Connection timed out")
        try:
            await ws.send_json({"type": "error", "content": "Response timed out"})
        except Exception:
            pass
    except Exception as e:
        logger.exception("Chat error")
        try:
            await ws.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
