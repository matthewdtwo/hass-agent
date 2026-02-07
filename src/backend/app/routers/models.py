from __future__ import annotations

import httpx
from fastapi import APIRouter

from app.config import settings
from app.models import ModelInfo

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
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_host}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                for m in data.get("models", []):
                    name = m["name"]
                    models.append(
                        ModelInfo(
                            id=f"ollama:{name}",
                            provider="ollama",
                            name=name,
                        )
                    )
    except Exception:
        pass  # Ollama not available

    return models
