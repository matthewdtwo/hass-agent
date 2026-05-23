from __future__ import annotations

import json

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings, _OPTIONS_FILE, _USER_CONFIG_FILE

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdate(BaseModel):
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    preferred_model: str | None = None


@router.get("")
async def get_config():
    return {
        # Mask the key — show asterisks if set, empty string if not
        "gemini_api_key": "***" if settings.gemini_api_key else "",
        "gemini_model": settings.gemini_model,
        "preferred_model": settings.preferred_model,
        "addon_mode": settings.addon_mode,
    }


@router.post("")
async def update_config(data: ConfigUpdate):
    updates: dict = {}
    if data.gemini_api_key is not None and data.gemini_api_key != "***":
        updates["gemini_api_key"] = data.gemini_api_key
    if data.gemini_model is not None:
        updates["gemini_model"] = data.gemini_model
    if data.preferred_model is not None:
        updates["preferred_model"] = data.preferred_model

    # Persist settings
    if settings.addon_mode:
        existing: dict = {}
        if _OPTIONS_FILE.exists():
            existing = json.loads(_OPTIONS_FILE.read_text())
        existing.update(updates)
        _OPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _OPTIONS_FILE.write_text(json.dumps(existing, indent=2))
    else:
        existing: dict = {}
        if _USER_CONFIG_FILE.exists():
            existing = json.loads(_USER_CONFIG_FILE.read_text())
        existing.update(updates)
        _USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _USER_CONFIG_FILE.write_text(json.dumps(existing, indent=2))

    # Update in-memory settings
    for key, val in updates.items():
        setattr(settings, key, val)

    return {"ok": True}
