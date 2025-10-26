"""Environment-driven application settings and helper accessor."""

from __future__ import annotations

"""Environment-driven application settings and helper accessor."""

from __future__ import annotations

from functools import cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and `.env`."""

    jina_api_key: SecretStr | None = Field(default=None, alias="JINA_API_KEY")
    slack_bot_token: SecretStr = Field(alias="SLACK_BOT_TOKEN")
    slack_signing_secret: SecretStr = Field(alias="SLACK_SIGNING_SECRET")
    temporal_host: str | None = None
    """`None` means start a local instance for development purposes"""
    temporal_port: int = 7233
    temporal_task_queue: str = "agent-task-queue"

    # Pydantic Settings config
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Pydantic Settings config
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance for use across the app lifecycle."""
    """Return a cached `Settings` instance for use across the app lifecycle."""
    return Settings()  # pyright: ignore[reportCallIssue]
