"""FastAPI dependency setup and lifespan state for Temporal and Slack."""

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast

from slack_sdk.web.async_client import AsyncWebClient as SlackClient

from pydantic_temporal_example.settings import get_settings
from pydantic_temporal_example.temporal.client import build_temporal_client

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI
    from starlette.requests import Request
    from temporalio.client import Client as TemporalClient


@asynccontextmanager
async def lifespan(_server: FastAPI) -> AsyncIterator[dict[str, Any]]:
    """Initialize shared app state (Temporal client, Slack bot user id) for FastAPI lifespan."""
    settings = get_settings()
    slack_client = SlackClient(token=settings.slack_bot_token.get_secret_value(), timeout=60)

    slack_bot_user_id: str = cast("str", (await slack_client.auth_test())["user_id"])  # pyright: ignore[reportUnknownMemberType]
    yield {"temporal_client": await build_temporal_client(), "slack_bot_user_id": slack_bot_user_id}


async def get_temporal_client(request: Request) -> TemporalClient:
    """Return the Temporal client injected in request state by the lifespan handler."""
    return request.state.temporal_client


async def get_slack_bot_user_id(request: Request) -> str:
    """Return the Slack bot user id injected in request state by the lifespan handler."""
    return request.state.slack_bot_user_id
