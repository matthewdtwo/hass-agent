import json
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_OPTIONS_FILE = Path("/data/options.json")
_USER_CONFIG_FILE = Path("data/user_config.json")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hass_url: str = "http://supervisor/core"
    hass_token: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    preferred_model: str = ""
    max_context_tokens: int = 16384
    openai_api_key: str = ""
    openai_base_url: str = ""
    db_path: str = "data/hass_agent.db"

    # Auth
    session_secret: str = secrets.token_hex(32)
    # Redirect URI that HA sends the browser to after login.
    # Must match what's used in the authorization request.
    oauth_redirect_uri: str = "http://localhost:5173/oauth/callback"

    # Addon mode: skip HA OAuth, trust HA Ingress auth headers
    addon_mode: bool = False


settings = Settings()

# In addon mode, overlay options from /data/options.json
if settings.addon_mode and _OPTIONS_FILE.exists():
    _opts = json.loads(_OPTIONS_FILE.read_text())
    for _key, _val in _opts.items():
        if hasattr(settings, _key) and _val:
            setattr(settings, _key, _val)
# In non-addon mode, overlay persisted user config from data/user_config.json
elif not settings.addon_mode and _USER_CONFIG_FILE.exists():
    _opts = json.loads(_USER_CONFIG_FILE.read_text())
    for _key, _val in _opts.items():
        if hasattr(settings, _key) and _val:
            setattr(settings, _key, _val)
