"""Web research agent that searches the web and returns structured results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import with_config
from pydantic_ai import (
    Agent,
    NativeOutput,
)

from pydantic_temporal_example.settings import get_settings
from pydantic_temporal_example.tools import jina_search_tool

if TYPE_CHECKING:
    from pydantic_temporal_example.agents.dispatch_agent import WebResearchRequest


@dataclass
@with_config(use_attribute_docstrings=True)
class WebResearchResponse:
    """Structured output for responses produced by the web research agent."""

    response: str | list[dict[str, Any]]
    """
    The formatted message to show to the user.

    This should either be a markdown text string, or valid Slack Block Kit blocks.
    """


# Settings are fetched in the builder to avoid import-time side effects.


def build_web_research_agent() -> Agent[WebResearchRequest, WebResearchResponse]:
    """Construct the web research agent, validating `JINA_API_KEY` at build time."""
    settings = get_settings()
    if settings.jina_api_key is None:
        msg = "JINA_API_KEY not set"
        raise ValueError(msg)
    api_key = settings.jina_api_key.get_secret_value()
    return Agent[WebResearchRequest, WebResearchResponse](
        model="openai-responses:gpt-5-mini",
        output_type=NativeOutput(WebResearchResponse),
        instructions="""You are a web research assistant.

    You will receive a WebResearchRequest with:
    - location: User's geographic location for local search
    - query: The research query
    - extra_info: Any additional context
    - thread_messages: The full Slack thread for reference

    - Disambiguate briefly if needed.
    - Use tools for current info; cite sources and dates inline.
    - Return concise Markdown or valid Slack Block Kit blocks.
    """,
        tools=[jina_search_tool(api_key)],
    )
