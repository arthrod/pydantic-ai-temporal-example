"""Web research agent that searches the web and returns structured results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import with_config
from pydantic_ai import Agent
from pydantic_ai_claude_code import ClaudeCodeModel, ClaudeCodeProvider

from pydantic_temporal_example.config import get_settings
from pydantic_temporal_example.tools import jina_search_tool

provider = ClaudeCodeProvider({"use_sandbox_runtime": False})
instance_model = ClaudeCodeModel("opus", provider=provider)
web_research_agent = Agent(model=instance_model)


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


def build_web_research_agent() -> Agent[None, WebResearchResponse] | None:
    """Construct the web research agent, validating `JINA_API_KEY` at build time."""
    settings = get_settings()
    jina_api_key = settings.JINA_API_KEY

    if jina_api_key == "":
        return None

    return Agent[None, WebResearchResponse](
        model=instance_model,
        output_type=WebResearchResponse,
        tools=[jina_search_tool(jina_api_key)],
        system_prompt="""You are a web research assistant.

    You will receive a WebResearchRequest with:
    - location: User's geographic location for local search
    - query: The research query
    - extra_info: Any additional context
    - thread_messages: The full Slack thread for reference

    - Disambiguate briefly if needed.
    - Use tools for current info; cite sources and dates inline.
    - Return concise Markdown or valid Slack Block Kit blocks.
    """,
    )
