from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter

from app.config import settings
from app.models import ModelInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=list[ModelInfo])
async def get_models() -> list[ModelInfo]:
    """Return available LLM models from Gemini and Ollama."""
    models: list[ModelInfo] = []

    # Gemini model from config
    known_models = {settings.gemini_model, "gemini-3-pro-preview"}
    for model in sorted(known_models):
        models.append(
            ModelInfo(
                id=f"google-gla:{model}",
                provider="gemini",
                name=model,
            )
        )

    # Ollama models
    if not settings.ollama_host:
        logger.debug("OLLAMA_HOST not set, skipping Ollama model discovery")
    else:
        url = f"{settings.ollama_host}/api/tags"
        logger.info("Fetching Ollama models from %s", url)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                logger.info("Ollama response: %s", resp.status_code)
                if resp.status_code == 200:
                    data = resp.json()
                    ollama_models = data.get("models", [])
                    logger.info("Ollama returned %d models: %s", len(ollama_models), [m["name"] for m in ollama_models])
                    for m in ollama_models:
                        name = m["name"]
                        models.append(
                            ModelInfo(
                                id=f"ollama:{name}",
                                provider="ollama",
                                name=name,
                            )
                        )
                else:
                    logger.warning("Ollama returned non-200: %s — %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.warning("Failed to reach Ollama at %s: %s: %s", url, type(exc).__name__, exc)

    return models
