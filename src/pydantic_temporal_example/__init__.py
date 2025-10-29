"""Example multi-agent Slack + Temporal application built with PydanticAI.

This package contains the FastAPI app, agents, models, and Temporal orchestration.
"""

import logfire

from .config import (
    get_github_agent_model,
    get_github_org,
    get_github_pat,
    get_jina_api_key,
)


def setup_logfire() -> logfire.Logfire:
    instance = logfire.configure(console=None)
    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx(capture_all=True)
    return instance


instance_logfire = setup_logfire()

__all__ = [
    "get_github_agent_model",
    "get_github_org",
    "get_github_pat",
    "get_jina_api_key",
    "instance_logfire",
]
