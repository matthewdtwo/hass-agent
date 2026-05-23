from __future__ import annotations

import secrets
import urllib.parse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.auth import get_ha_user_info, require_user
from app.config import settings
from app.db import get_or_create_user

router = APIRouter(tags=["auth"])


def _client_id_from_redirect_uri(redirect_uri: str) -> str:
    """HA uses the app's origin URL as client_id."""
    parsed = urllib.parse.urlparse(redirect_uri)
    return f"{parsed.scheme}://{parsed.netloc}"


@router.get("/api/auth/login")
async def login(request: Request):
    state = secrets.token_urlsafe(16)
    redirect_uri = settings.oauth_redirect_uri
    client_id = _client_id_from_redirect_uri(redirect_uri)

    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
    })
    response = RedirectResponse(url=f"{settings.hass_url}/auth/authorize?{params}")
    # Use a dedicated cookie rather than the session so the state survives
    # the proxy/redirect chain regardless of session middleware behaviour.
    response.set_cookie("oauth_state", state, httponly=True, samesite="lax", max_age=300, path="/")
    return response


async def _handle_callback(request: Request):
    state = request.query_params.get("state")
    stored_state = request.cookies.get("oauth_state")

    if not state or state != stored_state:
        raise HTTPException(status_code=400, detail="State mismatch — please try logging in again")

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    redirect_uri = settings.oauth_redirect_uri
    client_id = _client_id_from_redirect_uri(redirect_uri)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.hass_url}/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
            },
        )
        if not resp.is_success:
            raise HTTPException(status_code=502, detail=f"HA token exchange failed: {resp.text}")
        token_data = resp.json()

    access_token = token_data["access_token"]
    ha_user = await get_ha_user_info(access_token)

    db = request.app.state.db
    user = await get_or_create_user(
        db,
        email=f"ha_{ha_user['id']}@ha.local",
        name=ha_user.get("name", "HA User"),
    )
    request.session["user"] = user
    response = RedirectResponse(url="/")
    response.delete_cookie("oauth_state", path="/")
    return response


@router.get("/oauth/callback")
async def oauth_callback(request: Request):
    return await _handle_callback(request)


@router.get("/api/auth/callback")
async def api_callback(request: Request):
    return await _handle_callback(request)


@router.get("/api/auth/check")
async def check(request: Request):
    user = require_user(request)
    return user


@router.post("/api/auth/logout", status_code=204)
async def logout(request: Request):
    request.session.clear()
    return None
