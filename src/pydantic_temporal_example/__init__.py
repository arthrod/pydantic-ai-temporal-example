"""Example multi-agent Slack + Temporal application built with PydanticAI.

This package contains the FastAPI app, agents, models, and Temporal orchestration.
"""

from .config import GITHUB_AGENT_MODEL, GITHUB_ORG, GITHUB_PAT, JINA_API_KEY

__all__ = ['GITHUB_AGENT_MODEL', 'GITHUB_ORG', 'GITHUB_PAT', 'JINA_API_KEY']
