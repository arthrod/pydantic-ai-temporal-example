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
from pydantic_temporal_example.agents.github_agent import GitHubDependencies, github_agent
from pydantic_temporal_example.agents.web_research_agent import build_web_research_agent
from pydantic_temporal_example.models import (
    AppMentionEvent,
    CLIPromptEvent,
    CLIResponse,
    MessageChannelsEvent,
    SlackConversationsRepliesRequest,
    SlackMessageID,
    SlackReaction,
    SlackReply,
)
from pydantic_temporal_example.temporal.github_activities import fetch_github_prs
from pydantic_temporal_example.temporal.slack_activities import (
    slack_chat_post_message,
    slack_conversations_replies,
    slack_reactions_add,
    slack_reactions_remove,
)

temporal_dispatch_agent = TemporalAgent(dispatch_agent, name="dispatch_agent")
temporal_github_agent = TemporalAgent(github_agent, name="github_agent")

# Build web research agent only if JINA_API_KEY is configured
_web_research_agent = build_web_research_agent()
if _web_research_agent is not None:
    temporal_web_research_agent = TemporalAgent(_web_research_agent, name="web_research_agent")
else:
    temporal_web_research_agent = None


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
            # Extract query and create dependencies
            request = dispatcher_result.output
            # Default repo used when not specified in thread context
            deps = GitHubDependencies(repo_name="default-repo")
            result = await temporal_github_agent.run(request.query, deps=deps)
            response = result.output.response
        elif isinstance(dispatcher_result.output, WebResearchRequest):
            # Populate thread context and pass structured request
            if temporal_web_research_agent is None:
                response = "Web research is not available. Please configure JINA_API_KEY."
            else:
                request = dispatcher_result.output
                # Pass the query string to the agent
                result = await temporal_web_research_agent.run(request.query)
                response = result.output.response
        else:
            assert_never(dispatcher_result.output)

        # Post response
        await workflow.execute_activity(  # pyright: ignore[reportUnknownMemberType]
            slack_chat_post_message,
            SlackReply(thread=event_message, content=response),
            start_to_close_timeout=timedelta(seconds=10),
        )


@workflow.defn
class PeriodicGitHubPRCheckWorkflow:
    """Periodically checks GitHub PRs in a repository."""

    def __init__(self) -> None:
        """Initialize workflow state."""
        self._should_continue = True
        self._check_count = 0

    @workflow.run
    async def periodic_run(
        self,
        repo_name: str,
        check_interval_seconds: int = 30,
        query: str = "List all pull requests in the repository",
    ) -> None:
        """Main workflow loop: periodically fetches PRs from GitHub.

        Args:
            repo_name: Repository name to check (without organization)
            check_interval_seconds: How often to check for PRs (default: 30 seconds)
            query: The query/instruction to pass to the GitHub agent
        """
        workflow.logger.info(
            f"Starting periodic PR check for repository: {repo_name}, interval: {check_interval_seconds}s",
        )
        workflow.logger.info(f"Query: {query}")

        while self._should_continue:
            self._check_count += 1
            workflow.logger.info(f"Check #{self._check_count} - Fetching PRs from {repo_name}")

            try:
                # Fetch PRs using the GitHub activity
                result = await workflow.execute_activity(  # pyright: ignore[reportUnknownMemberType]
                    fetch_github_prs,
                    args=[repo_name, query],
                    start_to_close_timeout=timedelta(seconds=30),
                )

                workflow.logger.info(f"Check #{self._check_count} completed")
                workflow.logger.info(f"Response: {result.response}")

            except RuntimeError as e:
                workflow.logger.error(f"Error during check #{self._check_count}: {e}")

            # Wait before the next check
            workflow.logger.info(f"Waiting {check_interval_seconds}s before next check...")
            await workflow.sleep(check_interval_seconds)

    @workflow.signal
    async def stop(self) -> None:
        """Signal to stop the periodic checks."""
        workflow.logger.info("Received stop signal")
        self._should_continue = False

    @workflow.query
    def get_check_count(self) -> int:
        """Query to get the current check count."""
        return self._check_count


@workflow.defn
class CLIConversationWorkflow:
    """Orchestrates a CLI conversation: collects prompts, dispatches, and runs agents."""

    def __init__(self) -> None:
        """Initialize pending event queue and conversation message store."""
        self._pending_events: asyncio.Queue[CLIPromptEvent] = asyncio.Queue()
        self._conversation_messages: list[dict[str, Any]] = []
        self._response_ready: asyncio.Event = asyncio.Event()
        self._latest_response: CLIResponse | None = None
        self._repo_name: str = "default-repo"

    @workflow.run
    async def run(self) -> None:
        """Main workflow loop: waits for queued prompts and handles each one."""
        while True:
            await workflow.wait_condition(lambda: not self._pending_events.empty())
            while not self._pending_events.empty():
                event = self._pending_events.get_nowait()
                await self.handle_prompt(event)

    @workflow.signal
    async def submit_prompt(self, event: CLIPromptEvent) -> None:
        """Signal to enqueue a CLI prompt for processing."""
        await self._pending_events.put(event)

    @workflow.query
    def get_latest_response(self) -> CLIResponse | None:
        """Query to retrieve the most recent response."""
        return self._latest_response

    @workflow.query
    def get_conversation_history(self) -> list[dict[str, Any]]:
        """Query to retrieve the full conversation history."""
        return self._conversation_messages

    async def handle_prompt(self, event: CLIPromptEvent) -> None:
        """Process a CLI prompt: dispatch to agents and prepare response."""
        # Add user message to conversation history
        user_message = {
            "role": "user",
            "content": event.prompt,
            "timestamp": event.timestamp,
        }
        self._conversation_messages.append(user_message)

        # Get directive from the dispatch agent
        # Pass conversation messages as JSON string to dispatch agent
        stringified_conversation = json.dumps(self._conversation_messages, indent=2)
        dispatcher_result = await temporal_dispatch_agent.run(stringified_conversation)

        if isinstance(dispatcher_result.output, NoResponse):
            # Store empty response
            self._latest_response = CLIResponse(content="(No response needed)")
            return

        response: str | list[dict[str, Any]]
        if isinstance(dispatcher_result.output, SlackResponse):
            response = dispatcher_result.output.response
        elif isinstance(dispatcher_result.output, GitHubRequest):
            # Extract query and create dependencies
            request = dispatcher_result.output
            # Use configured repo name from workflow instance
            deps = GitHubDependencies(repo_name=self._repo_name)
            result = await temporal_github_agent.run(request.query, deps=deps)
            response = result.output.response
        elif isinstance(dispatcher_result.output, WebResearchRequest):
            # Delegate to web research agent
            if temporal_web_research_agent is None:
                response = "Web research is not available. Please configure JINA_API_KEY."
            else:
                request = dispatcher_result.output
                result = await temporal_web_research_agent.run(request.query)
                response = result.output.response
        else:
            assert_never(dispatcher_result.output)

        # Store response in conversation history
        assistant_message = {
            "role": "assistant",
            "content": response,
            "timestamp": workflow.now().isoformat(),
        }
        self._conversation_messages.append(assistant_message)

        # Set latest response for query
        self._latest_response = CLIResponse(
            content=response,
            metadata={
                "timestamp": assistant_message["timestamp"],
                "message_count": len(self._conversation_messages),
            },
        )
        self._response_ready.set()
