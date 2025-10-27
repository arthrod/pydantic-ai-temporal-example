from functools import cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file.

    Required environment variables:
        SLACK_BOT_TOKEN: OAuth token for Slack bot authentication
        SLACK_SIGNING_SECRET: Secret for verifying Slack request signatures

    Optional environment variables:
        TEMPORAL_HOST: Temporal server host (default: None for local testing)
        TEMPORAL_PORT: Temporal server port (default: 7233)
        TEMPORAL_TASK_QUEUE: Task queue name (default: "agent-task-queue")
    """

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    slack_bot_token: str | None = None
    slack_signing_secret: str | None = None
    temporal_host: str | None = None
    temporal_port: int = Field(default=7233, ge=1, le=65535, description='Temporal server port')
    temporal_task_queue: str = 'agent-task-queue'
    JINA_API_KEY: str = Field(default='', validation_alias=AliasChoices('JINA_API_KEY'))
    GITHUB_PAT: str = Field(default='', validation_alias=AliasChoices('GITHUB_PAT'))
    GITHUB_ORG: str = Field(default='arthrod', validation_alias=AliasChoices('GITHUB_ORG'))
    GITHUB_AGENT_MODEL: str = Field(default='claude-code:sonnet', validation_alias=AliasChoices('GITHUB_AGENT_MODEL'))


@cache
def get_settings() -> Settings:
    """Get cached application settings instance.

    Returns:
        Settings: Singleton settings instance loaded from environment.

    Note:
        Settings are cached after first call to avoid repeated environment reads.
    """
    return Settings()


JINA_API_KEY = get_settings().JINA_API_KEY
GITHUB_PAT = get_settings().GITHUB_PAT
GITHUB_ORG = get_settings().GITHUB_ORG
GITHUB_AGENT_MODEL: str
