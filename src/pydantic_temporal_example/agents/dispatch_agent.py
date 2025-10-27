"""Dispatcher agent that routes to Slack, web research, or GitHub."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import with_config
from pydantic_ai import Agent, WebSearchUserLocation
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool  # pyright: ignore[reportUnknownVariableType]
from pydantic_ai_claude_code import ClaudeCodeProvider

provider = ClaudeCodeProvider({'use_sandbox_runtime': False})
agent = Agent('claude-code:sonnet')


@dataclass
@with_config(use_attribute_docstrings=True)
class NoResponse:
    """A marker that indicates that you do not currently need to reply to the thread.

    You should use this when the most recent messages in the thread are not directed toward you,
    e.g. if other users are discussing something between themselves.

    If you select this, no response to the latest messages in the thread will be sent.
    """

    type: Literal['no-response']


@dataclass
@with_config(use_attribute_docstrings=True)
class SlackResponse:
    """A marker that indicates that you want to immediately send a response message.

    You can use this to request additional information from the user if they have not provided all the information
    necessary to make a WebResearchRequest.

    This tool provides a way to respond to the thread without triggering the web research agent.
    For example, if you ask the user a question, then they ask for clarification, you can use this to
    provide that clarification under the assumption that they will subsequently respond to your initial question.
    """

    type: Literal['slack-response']
    response: str | list[dict[str, Any]]
    """
    The response to show to the user. This should either be a markdown text string, or valid Slack blockkit blocks
    """


@dataclass
@with_config(use_attribute_docstrings=True)
class WebResearchRequest:
    """A marker that indicates that you are ready to delegate to the web research agent.

    If you have not already provided suggestions in the thread, you should generally use this tool whenever you have the
    necessary information to do so, unless the user has made a different request that is better handled by a direct
    response. If you don't have the necessary information, consider using the SlackResponse tool to request that
    additional information.
    """

    type: Literal['web-research-request']
    location: WebSearchUserLocation
    query: str
    extra_info: str | None
    thread_messages: list[dict[str, Any]] | None = None
    """Full Slack thread context for agent reference"""


@dataclass
@with_config(use_attribute_docstrings=True)
class GitHubRequest:
    """A marker that indicates that you are ready to delegate to the github agent."""

    type: Literal['github-request']
    query: str
    extra_info: str | None
    thread_messages: list[dict[str, Any]] | None = None
    """Full Slack thread context for agent reference"""


type DispatchResult = NoResponse | SlackResponse | WebResearchRequest | GitHubRequest

dispatch_agent = Agent(
    model='openai-responses:gpt-5-mini',
    output_type=[NoResponse, SlackResponse, WebResearchRequest, GitHubRequest],
    instructions="""
    You are a dispatch agent in an application designed to help a user with their requests.

    You will be provided with the contents of a slack thread the user is messaging you in.

    You will be triggered any time the user @-mentions you on slack, or when there is a reply to a thread in which you
    have been @-mentioned.

    Your goal should be to call, or collect enough information to call, the WebResearchRequest or GitHubRequest tool.

    The WebResearchRequest tool delegates to a specialized agent to do research on local options the user might be
    interested in and sends a response to the user's request. It takes a while to do this research, so you should not
    fill in the fields of the request by _guessing_ the user's preferences — if you are missing information, you must
    use the SlackResponse tool to request the necessary information from the user before making the request.

    The GitHubRequest tool delegates to a specialized agent to do research on GitHub repositories.

    If suggestions _have_ already been provided, you should NOT call the WebResearchRequest or GitHubRequest tool again
    unless the user provides new information that would _change_ the contents of the request. If they just respond to
    your suggestions, you can (optionally) use the search tools and just generate a SlackResponse directly.

    The SlackResponse tool can also be used to otherwise engage the user if appropriate.

    You should NOT attempt to produce suggestions for the user directly — always use the WebResearchRequest or
    GitHubRequest tool to produce the suggestions. However, you may use the duckduckgo tool to search the internet if
    the user asks a relevant question that shouldn't be used to produce a call to the WebResearchRequest or
    GitHubRequest tool.
    """,
    tools=[duckduckgo_search_tool()],
)
