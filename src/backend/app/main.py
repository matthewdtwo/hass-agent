from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.db import close_db, init_db
from app.ha_client import HAClient
from app.routers import auth, chat, models, sessions


class AuthMiddleware:
    """Reject unauthenticated requests to /api and /ws (except /api/auth)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path: str = scope["path"]

        # Allow auth endpoints and OAuth callback through
        if path.startswith("/api/auth") or path.startswith("/oauth"):
            await self.app(scope, receive, send)
            return

        # WebSocket auth is checked in the handler itself
        if scope["type"] == "websocket":
            await self.app(scope, receive, send)
            return

        # Require auth for /api routes
        if path.startswith("/api") or path.startswith("/ws"):
            conn = HTTPConnection(scope)
            if not conn.session.get("user"):
                response = JSONResponse(
                    {"detail": "Not authenticated"}, status_code=401
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
