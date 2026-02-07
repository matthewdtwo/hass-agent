from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ha_client import HAClient
from app.config import settings
from app.routers import chat, models


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ha_client = HAClient(settings.hass_url, settings.hass_token)
    await app.state.ha_client.connect()
    yield
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
