from functools import cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    slack_bot_token: str
    slack_signing_secret: str
    temporal_host: str | None = None
    temporal_port: int = 7233
    temporal_task_queue: str = "agent-task-queue"
    schedule_interval_seconds: int = 60
    repeat_worker: bool = False


@cache
def get_settings() -> Settings:
    return Settings()
