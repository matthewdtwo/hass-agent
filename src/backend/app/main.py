from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import close_db, init_db
from app.ha_client import HAClient
from app.routers import chat, models, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ha_client = HAClient(settings.hass_url, settings.hass_token)
    await app.state.ha_client.connect()
    app.state.db = await init_db(settings.db_path)
    yield
    await close_db(app.state.db)
    await app.state.ha_client.close()


app = FastAPI(title="HA Maintenance Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(models.router)
app.include_router(sessions.router)
