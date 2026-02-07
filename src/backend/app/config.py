import json
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_CREDS_FILE = _BACKEND_DIR / "oauth_credentials.json"


def _load_oauth_credentials() -> tuple[str, str]:
    """Load client_id and client_secret from oauth_credentials.json."""
    data = json.loads(_CREDS_FILE.read_text())
    web = data["web"]
    return web["client_id"], web["client_secret"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
    )

    hass_url: str
    hass_token: str
    ollama_host: str
    gemini_api_key: str
    gemini_model: str = "gemini-3-flash-preview"
    db_path: str = "data/hass_agent.db"

    # Auth
    session_secret: str = secrets.token_hex(32)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:5173/oauth/callback"


settings = Settings()

# Overlay OAuth credentials from JSON file if not set via env
if not settings.google_client_id and _CREDS_FILE.exists():
    _cid, _csec = _load_oauth_credentials()
    settings.google_client_id = _cid
    settings.google_client_secret = _csec
