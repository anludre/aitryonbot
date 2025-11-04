from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram / Webhook
    TELEGRAM_BOT_TOKEN: str
    PUBLIC_BASE_URL: Optional[str] = None
    WEBHOOK_SECRET: str = "local-dev"

    # Storage / Data
    DATA_DIR: str = "data"

    # Celery / Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # External APIs
    SEGMIND_API_KEY: Optional[str] = None


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def ensure_data_dirs(settings: Optional[Settings] = None) -> None:
    s = settings or get_settings()
    base = Path(s.DATA_DIR)
    for sub in ("models", "items", "outfits"):
        (base / sub).mkdir(parents=True, exist_ok=True)


