from functools import cache
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    slack_bot_token: str
    slack_signing_secret: str
    temporal_host: str | None = None
    temporal_port: int = 7233
    temporal_task_queue: str = "agent-task-queue"


@cache
def get_settings() -> Settings:
    if TYPE_CHECKING:
        return Settings(slack_bot_token="dummy", slack_signing_secret="dummy")
    return Settings()
