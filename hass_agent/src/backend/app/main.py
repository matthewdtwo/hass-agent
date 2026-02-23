import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.db import close_db, get_or_create_user, get_user_by_token, init_db
from app.ha_client import HAClient
from app.routers import auth, chat, models, sessions, tokens
from app.routers import config as config_router

_FRONTEND_DIR = Path(
    os.environ.get(
        "FRONTEND_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"),
    )
)


class AuthMiddleware:
    """Reject unauthenticated requests to /api and /ws (except /api/auth).

    In addon mode: auto-authenticates via the X-Hass-User-Id header that
    HA Ingress injects, so the login screen is never shown.
    Outside addon mode: supports session cookies and Bearer tokens.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path: str = scope["path"]

        # Static assets and non-API paths pass through freely
        if not path.startswith("/api") and not path.startswith("/ws"):
            await self.app(scope, receive, send)
            return

        conn = HTTPConnection(scope)

        # ── Addon mode: populate session from HA Ingress headers first ────
        # This must run before any early-returns (including /api/auth/check)
        # so that checkAuth() sees a user and the frontend never shows login.
        if settings.addon_mode and not conn.session.get("user"):
            headers = dict(scope.get("headers", []))
            ha_user_id = headers.get(b"x-hass-user-id", b"").decode()
            name = (
                headers.get(b"x-remote-user-display-name", b"").decode()
                or "HA User"
            )
            email = f"ha_{ha_user_id}@ha.local" if ha_user_id else "ha_admin@ha.local"
            db = scope["app"].state.db
            user = await get_or_create_user(db, email, name)
            conn.session["user"] = user

        # Allow auth endpoints and OAuth callback through
        if path.startswith("/api/auth") or path.startswith("/oauth"):
            await self.app(scope, receive, send)
            return

        # WebSocket auth is checked in the handler itself
        if scope["type"] == "websocket":
            await self.app(scope, receive, send)
            return

        # In addon mode the session is already set above — just continue
        if settings.addon_mode:
            await self.app(scope, receive, send)
            return

        # ── Standard mode: session cookie or Bearer token ─────────────────
        if conn.session.get("user"):
            await self.app(scope, receive, send)
            return

        auth_header = dict(scope.get("headers", [])).get(b"authorization", b"").decode()
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[7:]
            user = await get_user_by_token(scope["app"].state.db, raw_token)
            if user:
                scope["state"] = {**scope.get("state", {}), "token_user": user}
                await self.app(scope, receive, send)
                return

        response = JSONResponse(
            {"detail": "Not authenticated"}, status_code=401
        )
        await response(scope, receive, send)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    token_status = f"set ({len(settings.hass_token)} chars)" if settings.hass_token else "EMPTY"
    logger.info("Starting HA Agent: url=%s token=%s addon_mode=%s", settings.hass_url, token_status, settings.addon_mode)
    app.state.ha_client = HAClient(settings.hass_url, settings.hass_token)
    await app.state.ha_client.connect()
    app.state.db = await init_db(settings.db_path)
    yield
    await close_db(app.state.db)
    await app.state.ha_client.close()


app = FastAPI(title="HA Maintenance Agent", lifespan=lifespan)

# Middleware stack (outermost listed first):
# 1. SessionMiddleware — populates scope["session"] from cookie
# 2. AuthMiddleware — rejects unauthenticated /api requests
# 3. CORSMiddleware — handles CORS preflight
# Note: add_middleware prepends, so add in reverse order
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="ha_session",
    max_age=86400 * 7,
    same_site="lax",
    https_only=False,
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(models.router)
app.include_router(sessions.router)
app.include_router(tokens.router)
app.include_router(config_router.router)

# Serve the built frontend — must be mounted last so API routes take priority
if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="static")
