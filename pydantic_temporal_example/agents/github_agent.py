"""GitHub-focused agent returning structured responses for repository and issue tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import with_config
from pydantic_ai import Agent, NativeOutput


@dataclass
@with_config(use_attribute_docstrings=True)
class GitHubResponse:
    """Structured output produced by the GitHub agent."""

    response: str | list[dict[str, Any]]
    """
    The formatted message to show to the user.

    This should either be a markdown text string, or valid Slack blockkit blocks.
    """


github_agent = Agent(
    model="openai-responses:gpt-5-mini",
    output_type=NativeOutput(GitHubResponse),
    instructions="""The user wants help with a GitHub-related task.

    You should be able to answer questions about repositories, users, and issues.
    """,
    tools=[],
)
