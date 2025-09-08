import asyncio
import json
from datetime import timedelta
from typing import Any

import logfire
from pydantic_ai.durable_exec.temporal import TemporalAgent
from pydantic_core import to_json
from temporalio import workflow

from pydantic_temporal_example.agents.dinner_research_agent import (
    DinnerSuggestions,
    dinner_research_agent,
)
from pydantic_temporal_example.agents.dispatch_agent import NoResponse, SlackResponse, dispatch_agent
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
temporal_dinner_research_agent = TemporalAgent(dinner_research_agent, name="dinner_research_agent")


@workflow.defn
class SlackThreadWorkflow:
    def __init__(self) -> None:
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
        while True:
            await workflow.wait_condition(lambda: not self._pending_events.empty())
            while not self._pending_events.empty():
                event = self._pending_events.get_nowait()
                await self.handle_event(event)

    @workflow.signal
    async def submit_app_mention_event(self, event: AppMentionEvent):
        await self._pending_events.put(event)

    @workflow.signal
    async def submit_message_channels_event(self, event: MessageChannelsEvent):
        await self._pending_events.put(event)

    async def handle_event(self, event: AppMentionEvent | MessageChannelsEvent):
        thread = SlackMessageID(channel=event.channel, ts=event.reply_thread_ts)
        event_message = SlackMessageID(channel=event.channel, ts=event.ts)

        # Set a spinner reaction on the message for which a reply is being generated
        await workflow.execute_activity(  # pyright: ignore[reportUnknownMemberType]
            slack_reactions_add,
            SlackReaction(message=event_message, name="spin"),
            start_to_close_timeout=timedelta(seconds=10),
        )

        request = SlackConversationsRepliesRequest(channel=thread.channel, ts=thread.ts, oldest=self._most_recent_ts)
        new_messages = await workflow.execute_activity(  # pyright: ignore[reportUnknownMemberType]
            slack_conversations_replies,
            request,
            start_to_close_timeout=timedelta(seconds=10),
        )
        for message in new_messages:
            self._thread_messages.append(message)
        self._thread_messages.sort(key=lambda m: m["ts"])

        # TODO: Better-format the thread messages
        stringified_thread = json.dumps(self._thread_messages, indent=2)
        result = await handle_user_request(stringified_thread)

        if isinstance(result, NoResponse):
            return

        slack_reply = SlackReply(thread=thread, content=result.response)

        await asyncio.gather(
            # Remove the spinner reaction
            workflow.execute_activity(  # pyright: ignore[reportUnknownMemberType]
                slack_reactions_remove,
                SlackReaction(message=event_message, name="spin"),
                start_to_close_timeout=timedelta(seconds=10),
            ),
            # Post the new response
            workflow.execute_activity(  # pyright: ignore[reportUnknownMemberType]
                slack_chat_post_message,
                slack_reply,
                start_to_close_timeout=timedelta(seconds=10),
            ),
        )


@logfire.instrument
async def handle_user_request(stringified_thread: str) -> NoResponse | SlackResponse | DinnerSuggestions:
    dispatch_result = await temporal_dispatch_agent.run(stringified_thread)
    if isinstance(request := dispatch_result.output, NoResponse | SlackResponse):
        return request
    dinner_choosing_result = await temporal_dinner_research_agent.run(
        f"User info: {to_json(dispatch_result.output, indent=2).decode()}"
    )
    return dinner_choosing_result.output
