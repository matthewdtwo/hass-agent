from __future__ import annotations

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request

from app.config import settings

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def get_current_user(request: Request) -> dict | None:
    """Return user dict from session, or None if not authenticated."""
    return request.session.get("user")


def require_user(request: Request) -> dict:
    """Return user dict from session, or raise 401."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
