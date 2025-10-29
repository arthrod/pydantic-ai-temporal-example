"""FastAPI dependency setup and lifespan state for Temporal and Slack."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

import logfire
from fastapi import FastAPI
from slack_sdk.web.async_client import AsyncWebClient as SlackClient
from starlette.requests import Request
from temporalio.client import Client as TemporalClient

from pydantic_temporal_example.config import get_settings
from pydantic_temporal_example.temporal.client import build_temporal_client


async def _initialize_slack_client(token: str) -> tuple[SlackClient, str]:
    """Initialize Slack client and retrieve bot user ID.

    Args:
        token: Slack bot token

    Returns:
        Tuple of (SlackClient, bot_user_id)

    Raises:
        Exception: If Slack authentication fails
    """
    slack_client = SlackClient(token=token, timeout=60)
    slack_bot_user_id = cast("str", (await slack_client.auth_test())["user_id"])  # pyright: ignore[reportUnknownMemberType]
    logfire.info("Slack client initialized successfully")
    return slack_client, slack_bot_user_id


async def _close_client_safely(client: TemporalClient | SlackClient | None, client_name: str) -> None:
    """Safely close a client with error handling.

    Args:
        client: Client to close (Temporal or Slack)
        client_name: Name of the client for logging
    """
    if client is None:
        return
    try:
        # Both TemporalClient and SlackClient have close() method
        await client.close()  # type: ignore[union-attr]
        logfire.info(f"{client_name} closed successfully")
    except BaseException:  # noqa: BLE001
        # Catch all exceptions during cleanup to avoid suppressing original errors
        logfire.exception(f"Error closing {client_name}")


@asynccontextmanager
async def lifespan(_server: FastAPI) -> AsyncIterator[dict[str, Any]]:
    """Initialize shared app state (Temporal client, Slack bot user id) for FastAPI lifespan."""
    settings = get_settings()
    slack_client: SlackClient | None = None
    temporal_client: TemporalClient | None = None
    slack_bot_user_id: str | None = None

    try:
        # Initialize Slack client (optional)
        if settings.slack_bot_token:
            slack_client, slack_bot_user_id = await _initialize_slack_client(settings.slack_bot_token)
        else:
            logfire.info("Slack token not provided, Slack integration disabled")

        # Initialize Temporal client
        temporal_client = await build_temporal_client()

        try:
            yield {"temporal_client": temporal_client, "slack_bot_user_id": slack_bot_user_id}
        finally:
            # Cleanup: close both clients
            await _close_client_safely(temporal_client, "Temporal client")
            await _close_client_safely(slack_client, "Slack client")
    except BaseException:
        # If initialization failed, still attempt cleanup
        await _close_client_safely(temporal_client, "Temporal client")
        await _close_client_safely(slack_client, "Slack client")
        raise


async def get_temporal_client(request: Request) -> TemporalClient:
    """Return the Temporal client injected in request state by the lifespan handler."""
    return request.state.temporal_client


async def get_slack_bot_user_id(request: Request) -> str | None:
    """Return the Slack bot user id injected in request state by the lifespan handler."""
    return request.state.slack_bot_user_id
