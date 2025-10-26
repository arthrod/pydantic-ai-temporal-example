"""Web research agent that searches the web and returns structured results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import with_config
from pydantic_ai import (
    Agent,
    NativeOutput,
)

from pydantic_temporal_example.settings import get_settings
from pydantic_temporal_example.tools import jina_search_tool


@dataclass
class WebSearchResult:
    """A single web search hit."""

    title: str
    url: str | None
    summary: str


@dataclass
@with_config(use_attribute_docstrings=True)
class WebResearchResponse:
    """Structured output for responses produced by the web research agent."""

    response: str | list[dict[str, Any]]
    """
    The formatted message to show to the user.

    This should either be a markdown text string, or valid Slack blockkit blocks.
    """


settings = get_settings()
# Defer validation to builder below to avoid import-time failures.


def build_web_research_agent() -> Agent[None, WebResearchResponse]:
    """Construct the web research agent, validating `JINA_API_KEY` at build time."""
    settings = get_settings()
    if settings.jina_api_key is None:
        msg = "JINA_API_KEY not set"
        raise ValueError(msg)
    api_key = settings.jina_api_key.get_secret_value()
    return Agent[None, WebResearchResponse](
        model="openai-responses:gpt-5-mini",
        output_type=NativeOutput(WebResearchResponse),
        instructions="""The user wants help with a web research task.

    Using the provided information, use the tools at your disposal to research what you think the user might want.
    """,
        tools=[jina_search_tool(api_key)],
    )
