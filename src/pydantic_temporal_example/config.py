"""Configuration management for the application using pydantic-settings."""

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
        APP_HOST: FastAPI app host for CLI communication (default: "127.0.0.1")
        APP_PORT: FastAPI app port for CLI communication (default: 4000)
        CLI_TIMEOUT: CLI request timeout in seconds (default: 30)
        MAX_RETRY_ATTEMPTS: Maximum retry attempts for workflow operations (default: 3)
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    slack_bot_token: str | None = None
    slack_signing_secret: str | None = None
    temporal_host: str | None = None
    temporal_port: int = Field(default=7233, ge=1, le=65535, description="Temporal server port")
    temporal_task_queue: str = "agent-task-queue"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=4000, ge=1, le=65535, description="FastAPI app port")
    cli_timeout: int = Field(default=30, ge=1, le=300, description="CLI request timeout in seconds")
    max_retry_attempts: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    JINA_API_KEY: str = Field(default="", validation_alias=AliasChoices("JINA_API_KEY"))
    GITHUB_PAT: str = Field(default="", validation_alias=AliasChoices("GITHUB_PAT"))
    GITHUB_ORG: str = Field(default="arthrod", validation_alias=AliasChoices("GITHUB_ORG"))
    GITHUB_AGENT_MODEL: str = Field(default="claude-code:sonnet", validation_alias=AliasChoices("GITHUB_AGENT_MODEL"))
    LOGFIRE_API_KEY: str = Field(default="", validation_alias=AliasChoices("LOGFIRE_API_KEY"))


@cache
def get_settings() -> Settings:
    """Get cached application settings instance.

    Returns:
        Settings: Singleton settings instance loaded from environment.

    Note:
        Settings are cached after first call to avoid repeated environment reads.
    """
    return Settings()


# Helper functions to lazily access settings values
# These avoid module-level Settings() initialization which conflicts with Temporal's workflow sandbox
def get_jina_api_key() -> str:
    """Get JINA_API_KEY from settings."""
    return get_settings().JINA_API_KEY


def get_github_pat() -> str:
    """Get GITHUB_PAT from settings."""
    return get_settings().GITHUB_PAT


def get_github_org() -> str:
    """Get GITHUB_ORG from settings."""
    return get_settings().GITHUB_ORG


def get_github_agent_model() -> str:
    """Get GITHUB_AGENT_MODEL from settings."""
    return get_settings().GITHUB_AGENT_MODEL


def get_logfire_api_key() -> str:
    """Get LOGFIRE_API_KEY from settings."""
    return get_settings().LOGFIRE_API_KEY
