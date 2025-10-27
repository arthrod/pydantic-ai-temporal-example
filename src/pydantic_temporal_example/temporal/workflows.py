"""Temporal workflows orchestrating Slack threads and agent dispatch."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from typing import Any, assert_never

from pydantic_ai.durable_exec.temporal import TemporalAgent
from temporalio import workflow

from pydantic_temporal_example.agents.dispatch_agent import (
    GitHubRequest,
    NoResponse,
    SlackResponse,
    WebResearchRequest,
    dispatch_agent,
)
from pydantic_temporal_example.agents.github_agent import github_agent
from pydantic_temporal_example.agents.web_research_agent import build_web_research_agent
from pydantic_temporal_example.models import (
    AppMentionEvent,
    MessageChannelsEvent,
    SlackConversationsRepliesRequest,
    SlackMessageID,
    SlackReaction,
    SlackReply,
)
from pydantic_temporal_example.temporal.slack_activities import (
    slack_chat_post_message,
    slack_conversations_replies,
    slack_reactions_add,
    slack_reactions_remove,
)

temporal_dispatch_agent = TemporalAgent(dispatch_agent, name="dispatch_agent")
temporal_github_agent = TemporalAgent(github_agent, name="github_agent")
temporal_web_research_agent = TemporalAgent(build_web_research_agent(), name="web_research_agent")


@workflow.defn
class SlackThreadWorkflow:
    """Orchestrates a Slack thread: collects messages, dispatches, and runs agents."""

    def __init__(self) -> None:
        """Initialize pending event queue and thread message store."""
        self._pending_events: asyncio.Queue[AppMentionEvent | MessageChannelsEvent] = asyncio.Queue()
        self._thread_messages: list[dict[str, Any]] = []

    @property
    def _most_recent_ts(self) -> str | None:
        if not self._thread_messages:
            return None
        # assume _thread_messages is always sorted by ts
        return self._thread_messages[-1]["ts"]

    @workflow.run
    async def run(self) -> None:
        """Main workflow loop: waits for queued events and handles each one."""
        while True:
            await workflow.wait_condition(lambda: not self._pending_events.empty())
            while not self._pending_events.empty():
                event = self._pending_events.get_nowait()
                await self.handle_event(event)

    @workflow.signal
    async def submit_message_channels_event(self, event: MessageChannelsEvent) -> None:
        """Signal to enqueue a message channels event for processing."""
        await self._pending_events.put(event)

    @workflow.signal
    async def submit_app_mention_event(self, event: AppMentionEvent) -> None:
        """Signal to enqueue an app mention event for processing."""
        await self._pending_events.put(event)

    async def handle_event(self, event: AppMentionEvent | MessageChannelsEvent) -> None:
        """Process a Slack event: fetch updates, dispatch to agents, and post reply."""
        # add thinking reaction immediately
        most_recent_ts = self._most_recent_ts or event.event_ts
        event_message = SlackMessageID(channel=event.channel, ts=most_recent_ts)

        await workflow.execute_activity(  # pyright: ignore[reportUnknownMemberType]
            slack_reactions_add,
            SlackReaction(message=event_message, name="spin"),
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Get new messages in the thread
        request = SlackConversationsRepliesRequest(
            channel=event.channel,
            ts=event.reply_thread_ts,
            oldest=most_recent_ts,
        )
        new_messages: list[dict[str, Any]] = await workflow.execute_activity(  # pyright: ignore[reportUnknownMemberType]
            slack_conversations_replies,
            request,
            start_to_close_timeout=timedelta(seconds=10),
        )
        self._thread_messages.extend(new_messages)

        # Get directive from the dispatch agent
        # Pass thread messages as JSON string to dispatch agent
        stringified_thread = json.dumps(self._thread_messages, indent=2)
        dispatcher_result = await temporal_dispatch_agent.run(stringified_thread)

        if isinstance(dispatcher_result.output, NoResponse):
            return

        # remove thinking reaction before posting a message
        await workflow.execute_activity(  # pyright: ignore[reportUnknownMemberType]
            slack_reactions_remove,
            SlackReaction(message=event_message, name="spin"),
            start_to_close_timeout=timedelta(seconds=10),
        )

        response: str | list[dict[str, Any]]
        if isinstance(dispatcher_result.output, SlackResponse):
            response = dispatcher_result.output.response
        elif isinstance(dispatcher_result.output, GitHubRequest):
            # Populate thread context and pass structured request
            request = dispatcher_result.output
            request.thread_messages = self._thread_messages
            result = await temporal_github_agent.run(request)
            response = result.output.response
        elif isinstance(dispatcher_result.output, WebResearchRequest):
            # Populate thread context and pass structured request
            request = dispatcher_result.output
            request.thread_messages = self._thread_messages
            result = await temporal_web_research_agent.run(request)
            response = result.output.response
        else:
            assert_never(dispatcher_result.output)

        # Post response
        await workflow.execute_activity(  # pyright: ignore[reportUnknownMemberType]
            slack_chat_post_message,
            SlackReply(thread=event_message, content=response),
            start_to_close_timeout=timedelta(seconds=10),
        )
