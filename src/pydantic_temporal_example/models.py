"""Pydantic models for Slack events, replies, and request payloads."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Discriminator, TypeAdapter


class MessageChannelsEvent(BaseModel):
    """Slack `message` event with channel context and thread metadata."""

    type: Literal["message"]
    user: str
    text: str
    ts: str
    channel: str
    event_ts: str
    channel_type: str
    thread_ts: str | None = None

    @property
    def reply_thread_ts(self) -> str:
        """Timestamp to reply in thread, falling back to message `ts`."""
        return self.thread_ts or self.ts


class AppMentionEvent(BaseModel):
    """Slack `app_mention` event capturing the mention context in a thread."""

    type: Literal["app_mention"]
    user: str
    text: str
    ts: str
    channel: str
    event_ts: str
    thread_ts: str | None = None

    @property
    def reply_thread_ts(self) -> str:
        """Timestamp to reply in thread, falling back to message `ts`."""
        return self.thread_ts or self.ts


class URLVerificationEvent(BaseModel):
    """Slack Events API URL verification challenge payload."""

    type: Literal["url_verification"]
    token: str
    challenge: str


type SlackEvent = Annotated[
    AppMentionEvent | MessageChannelsEvent,
    Discriminator("type"),
]  # extendable for other event types; see https://docs.slack.dev/reference/events/


class SlackEventsAPIBody(BaseModel):
    """Envelope for Slack Events API callbacks carrying the event and metadata."""

    token: str
    team_id: str  # | None = None
    api_app_id: str  # | None = None
    event: SlackEvent
    type: Literal["event_callback"]
    event_id: str
    event_time: int
    authed_users: list[str] | None = None


SlackEventsAPIBodyAdapter: TypeAdapter[SlackEventsAPIBody | URLVerificationEvent | dict[str, Any]] = TypeAdapter(
    Annotated[SlackEventsAPIBody | URLVerificationEvent, Discriminator("type")] | dict[str, Any],
)


class SlackMessageID(BaseModel):
    """Identifier for a Slack message, consisting of channel and timestamp."""

    channel: str
    ts: str


class SlackReply(BaseModel):
    """A response payload to post in a Slack thread."""

    thread: SlackMessageID
    content: str | list[dict[str, Any]]

    @property
    def text(self) -> str | None:
        """Plain text response when `content` is a string; otherwise `None`."""
        return self.content if isinstance(self.content, str) else None

    @property
    def blocks(self) -> list[dict[str, Any]] | None:
        """Block Kit payload when `content` is blocks; otherwise `None`."""
        return self.content if not isinstance(self.content, str) else None


class SlackReaction(BaseModel):
    """A reaction event targeting a specific Slack message."""

    message: SlackMessageID
    name: str


class SlackConversationsRepliesRequest(BaseModel):
    """Request parameters to fetch replies for a Slack thread."""

    # See https://docs.slack.dev/reference/methods/conversations.replies/

    channel: str
    ts: str
    oldest: str | None  # only include messages after this unix timestamp
