"""Example multi-agent Slack + Temporal application built with PydanticAI.

This package contains the FastAPI app, agents, models, and Temporal orchestration.
"""

import logfire

from .config import GITHUB_AGENT_MODEL, GITHUB_ORG, GITHUB_PAT, JINA_API_KEY


def setup_logfire() -> logfire.Logfire:
    instance = logfire.configure(console=None)
    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx(capture_all=True)
    return instance


instance_logfire = setup_logfire()

__all__ = ["GITHUB_AGENT_MODEL", "GITHUB_ORG", "GITHUB_PAT", "JINA_API_KEY", "instance_logfire"]
