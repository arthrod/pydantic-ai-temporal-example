from functools import cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    slack_bot_token: str
    slack_signing_secret: str
    temporal_host: str | None = None
    """`None` means start a local instance for development purposes"""
    temporal_port: int = 7233
    temporal_task_queue: str = "agent-task-queue"


@cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
