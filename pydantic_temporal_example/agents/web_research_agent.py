from dataclasses import dataclass
from typing import Any

from pydantic import with_config
from pydantic_ai import (
    Agent,
    NativeOutput,
)
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool  # pyright: ignore[reportUnknownVariableType]


@dataclass
class WebSearchResult:
    restaurant_name: str
    restaurant_address: str | None
    recommended_dishes: str


@dataclass
@with_config(use_attribute_docstrings=True)
class WebResearchResponse:
    response: str | list[dict[str, Any]]
    """
    The formatted message to show to the user.

    This should either be a markdown text string, or valid Slack blockkit blocks.
    """


web_research_agent = Agent(
    model="openai-responses:gpt-5-mini",
    output_type=NativeOutput(WebResearchResponse),
    instructions="""The user wants help with a web research task.

    Using the provided information, use the tools at your disposal to research what you think the user might want.
    """,
    tools=[duckduckgo_search_tool()],
)
