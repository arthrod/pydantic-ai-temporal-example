"""Temporal activities integrating with Slack API (post, replies, reactions)."""

# Enable postponed evaluation of annotations
from __future__ import annotations

# pyright: reportUnknownMemberType=false
from typing import TYPE_CHECKING, Any, cast

import logfire
from slack_sdk.web.async_client import AsyncWebClient as SlackClient
from temporalio import activity

from pydantic_temporal_example.settings import get_settings

if TYPE_CHECKING:
    from pydantic_temporal_example.models import (
        SlackConversationsRepliesRequest,
        SlackMessageID,
        SlackReaction,
        SlackReply,
    )


@activity.defn
@logfire.instrument
async def slack_conversations_replies(request: SlackConversationsRepliesRequest) -> list[dict[str, Any]]:
    """Fetch messages in a Slack thread, handling pagination via `has_more` and `cursor`."""
    has_more = True
    cursor = None
    messages: list[dict[str, Any]] = []
    while has_more:
        response = await _get_slack_client().conversations_replies(
            channel=request.channel,
            ts=request.ts,
            oldest=request.oldest,
            cursor=cursor,
        )
        response_messages = cast("list[dict[str, Any]]", response["messages"])
        messages.extend(response_messages)
        has_more = bool(response.get("has_more", False))
        if has_more:
            cursor = response.get("response_metadata", {}).get("next_cursor") or None

    return messages


@activity.defn
@logfire.instrument
async def slack_chat_post_message(reply: SlackReply) -> dict[str, Any]:
    """Post a message or blocks to the Slack thread identified by `reply.thread`."""
    response = await _get_slack_client().chat_postMessage(
        channel=reply.thread.channel,
        thread_ts=reply.thread.ts,
        text=reply.text,
        blocks=reply.blocks,
    )
    return cast("dict[str, Any]", response.data)


@activity.defn
@logfire.instrument
async def slack_chat_delete(message: SlackMessageID) -> dict[str, Any]:
    """Delete a Slack message given its channel and timestamp."""
    response = await _get_slack_client().chat_delete(
        channel=message.channel,
        ts=message.ts,
    )
    return cast("dict[str, Any]", response.data)


@activity.defn
@logfire.instrument
async def slack_reactions_add(reaction: SlackReaction) -> dict[str, Any]:
    """Add a reaction to the specified Slack message."""
    response = await _get_slack_client().reactions_add(
        name=reaction.name,
        channel=reaction.message.channel,
        timestamp=reaction.message.ts,
    )
    return cast("dict[str, Any]", response.data)


@activity.defn
@logfire.instrument
async def slack_reactions_remove(reaction: SlackReaction) -> dict[str, Any]:
    """Remove a reaction from the specified Slack message."""
    response = await _get_slack_client().reactions_remove(
        name=reaction.name,
        channel=reaction.message.channel,
        timestamp=reaction.message.ts,
    )
    return cast("dict[str, Any]", response.data)


ALL_SLACK_ACTIVITIES = [
    slack_conversations_replies,
    slack_chat_post_message,
    slack_chat_delete,
    slack_reactions_add,
    slack_reactions_remove,
]


def _get_slack_client() -> SlackClient:
    settings = get_settings()
    return SlackClient(token=settings.slack_bot_token.get_secret_value(), timeout=60)
