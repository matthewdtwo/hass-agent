from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
    )

    hass_url: str
    hass_token: str
    ollama_host: str
    gemini_api_key: str
    gemini_model: str = "gemini-3-flash-preview"


settings = Settings()
