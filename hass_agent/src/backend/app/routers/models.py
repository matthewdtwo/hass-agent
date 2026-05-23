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
    """Return available LLM models from Gemini and OpenAI-compatible servers."""
    models: list[ModelInfo] = []

    # Gemini models — only if API key is configured
    if settings.gemini_api_key:
        known_models = {settings.gemini_model, "gemini-3.1-flash-lite"}
        for model in sorted(known_models):
            models.append(
                ModelInfo(
                    id=f"google-gla:{model}",
                    provider="gemini",
                    name=model,
                )
            )
    else:
        logger.debug("GEMINI_API_KEY not set, skipping Gemini model discovery")

    # OpenAI-compatible models (llama.cpp, LM Studio, etc.)
    if not settings.openai_base_url:
        logger.debug("OPENAI_BASE_URL not set, skipping OpenAI model discovery")
    else:
        url = f"{settings.openai_base_url.rstrip('/')}/v1/models"
        logger.info("Fetching OpenAI-compatible models from %s", url)
        headers = {}
        if settings.openai_api_key:
            headers["Authorization"] = f"Bearer {settings.openai_api_key}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=headers)
                logger.info("OpenAI-compatible server response: %s", resp.status_code)
                if resp.status_code == 200:
                    data = resp.json()
                    openai_models = data.get("data", [])
                    logger.info("OpenAI server returned %d models", len(openai_models))
                    for m in openai_models:
                        name = m["id"]
                        models.append(
                            ModelInfo(
                                id=f"openai:{name}",
                                provider="openai",
                                name=name,
                            )
                        )
                else:
                    logger.warning("OpenAI server returned non-200: %s — %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.warning("Failed to reach OpenAI server at %s: %s: %s", url, type(exc).__name__, exc)

    return models
