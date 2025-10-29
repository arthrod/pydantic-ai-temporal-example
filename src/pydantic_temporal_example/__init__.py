"""Example multi-agent Slack + Temporal application built with PydanticAI.

This package contains the FastAPI app, agents, models, and Temporal orchestration.
"""

from .config import (
    get_github_agent_model,
    get_github_org,
    get_github_pat,
    get_jina_api_key,
)

__all__ = [
    "get_github_agent_model",
    "get_github_org",
    "get_github_pat",
    "get_jina_api_key",
]
