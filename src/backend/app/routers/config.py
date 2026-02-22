from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/config", tags=["config"])

_OPTIONS_FILE = Path("/data/options.json")


class ConfigUpdate(BaseModel):
    ollama_host: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None


@router.get("")
async def get_config():
    return {
        "ollama_host": settings.ollama_host,
        # Mask the key — show asterisks if set, empty string if not
        "gemini_api_key": "***" if settings.gemini_api_key else "",
        "gemini_model": settings.gemini_model,
        "addon_mode": settings.addon_mode,
    }


@router.post("")
async def update_config(data: ConfigUpdate):
    updates: dict = {}
    if data.ollama_host is not None:
        updates["ollama_host"] = data.ollama_host
    if data.gemini_api_key is not None and data.gemini_api_key != "***":
        updates["gemini_api_key"] = data.gemini_api_key
    if data.gemini_model is not None:
        updates["gemini_model"] = data.gemini_model

    # Persist to /data/options.json in addon mode
    if settings.addon_mode:
        existing: dict = {}
        if _OPTIONS_FILE.exists():
            existing = json.loads(_OPTIONS_FILE.read_text())
        existing.update(updates)
        _OPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _OPTIONS_FILE.write_text(json.dumps(existing, indent=2))

    # Update in-memory settings
    for key, val in updates.items():
        setattr(settings, key, val)

    return {"ok": True}
