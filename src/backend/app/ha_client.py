from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
import websockets

logger = logging.getLogger(__name__)


class HAClient:
    """Async client for Home Assistant REST API."""

    def __init__(self, url: str, token: str) -> None:
        self._url = url.rstrip("/")
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._http: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=self._url,
            headers=self._headers,
            timeout=30.0,
        )

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()

    # ------------------------------------------------------------------
    # REST helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, **params: Any) -> Any:
        assert self._http is not None
        resp = await self._http.get(f"/api/{path}", params=params or None)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, data: Any = None) -> Any:
        assert self._http is not None
        resp = await self._http.post(f"/api/{path}", json=data)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # States
    # ------------------------------------------------------------------

    async def get_states(self) -> list[dict[str, Any]]:
        return await self._get("states")

    async def get_entity_state(self, entity_id: str) -> dict[str, Any]:
        return await self._get(f"states/{entity_id}")

    # ------------------------------------------------------------------
    # Config, services
    # ------------------------------------------------------------------

    async def get_config(self) -> dict[str, Any]:
        return await self._get("config")

    async def get_services(self) -> list[dict[str, Any]]:
        return await self._get("services")

    # ------------------------------------------------------------------
    # History & logs
    # ------------------------------------------------------------------

    async def get_history(
        self,
        entity_id: str,
        hours: int = 24,
    ) -> list[list[dict[str, Any]]]:
        start = (datetime.now() - timedelta(hours=hours)).isoformat()
        return await self._get(
            f"history/period/{start}",
            filter_entity_id=entity_id,
            minimal_response="",
        )

    async def get_logbook(
        self,
        entity_id: str | None = None,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        start = (datetime.now() - timedelta(hours=hours)).isoformat()
        params: dict[str, Any] = {}
        if entity_id:
            params["entity"] = entity_id
        return await self._get(f"logbook/{start}", **params)

    async def get_error_log(self) -> str:
        assert self._http is not None
        resp = await self._http.get("/api/error_log")
        resp.raise_for_status()
        return resp.text

    # ------------------------------------------------------------------
    # Services / actions
    # ------------------------------------------------------------------

    async def call_service(
        self,
        domain: str,
        service: str,
        data: dict[str, Any] | None = None,
    ) -> Any:
        return await self._post(f"services/{domain}/{service}", data or {})

    # ------------------------------------------------------------------
    # Templates & config check
    # ------------------------------------------------------------------

    async def render_template(self, template: str) -> str:
        assert self._http is not None
        resp = await self._http.post("/api/template", json={"template": template})
        resp.raise_for_status()
        return resp.text

    async def check_config(self) -> dict[str, Any]:
        return await self._post("config/core/check_config")

    # ------------------------------------------------------------------
    # One-shot WebSocket (connect → auth → command → close)
    # ------------------------------------------------------------------

    async def _ws_oneshot(self, command: dict[str, Any]) -> Any:
        """Open a short-lived WS connection, send one command, return result."""
        ws_url = self._url.replace("http", "ws", 1) + "/api/websocket"
        async with websockets.connect(ws_url) as ws:
            # 1. auth_required
            msg = json.loads(await ws.recv())
            if msg.get("type") != "auth_required":
                raise RuntimeError(f"Unexpected WS message: {msg}")
            # 2. authenticate
            await ws.send(json.dumps({"type": "auth", "access_token": self._token}))
            msg = json.loads(await ws.recv())
            if msg.get("type") != "auth_ok":
                raise RuntimeError(f"WS auth failed: {msg}")
            # 3. send command
            command["id"] = 1
            await ws.send(json.dumps(command))
            msg = json.loads(await ws.recv())
            if not msg.get("success"):
                raise RuntimeError(f"WS command failed: {msg}")
            return msg.get("result")

    async def remove_entity(self, entity_id: str) -> dict[str, Any]:
        """Remove an entity from the HA entity registry via WS."""
        await self._ws_oneshot({
            "type": "config/entity_registry/remove",
            "entity_id": entity_id,
        })
        return {"removed": entity_id}
