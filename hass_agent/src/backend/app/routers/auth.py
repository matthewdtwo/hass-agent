from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.auth import oauth, require_user
from app.config import settings
from app.db import get_or_create_user

router = APIRouter(tags=["auth"])


@router.get("/api/auth/login")
async def login(request: Request):
    return await oauth.google.authorize_redirect(
        request, settings.google_redirect_uri
    )


async def _handle_callback(request: Request):
    """Shared callback logic for OAuth redirect."""
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo", {})

    db = request.app.state.db
    user = await get_or_create_user(
        db,
        email=userinfo["email"],
        name=userinfo.get("name", userinfo["email"]),
        picture=userinfo.get("picture"),
    )

    request.session["user"] = user
    return RedirectResponse(url="/")


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
