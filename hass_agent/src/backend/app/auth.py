from __future__ import annotations

import json

import websockets
from fastapi import HTTPException, Request

from app.config import settings


async def get_ha_user_info(access_token: str) -> dict:
    """Authenticate to HA WebSocket and return the current user's profile."""
    ws_url = (
        settings.hass_url
        .replace("https://", "wss://")
        .replace("http://", "ws://")
    ) + "/api/websocket"

    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # auth_required
        await ws.send(json.dumps({"type": "auth", "access_token": access_token}))
        auth_resp = json.loads(await ws.recv())
        if auth_resp.get("type") != "auth_ok":
            raise ValueError("HA authentication rejected the access token")

        await ws.send(json.dumps({"id": 1, "type": "auth/current_user"}))
        user_resp = json.loads(await ws.recv())

    if not user_resp.get("success"):
        raise ValueError("Could not retrieve HA user info")
    return user_resp["result"]


def get_current_user(request: Request) -> dict | None:
    """Return user dict from session or Bearer token, or None."""
    return request.session.get("user") or getattr(request.state, "token_user", None)


def require_user(request: Request) -> dict:
    """Return user dict from session or Bearer token, or raise 401."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
