"""FastAPI dependency setup and lifespan state for Temporal and Slack."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI
from slack_sdk.web.async_client import AsyncWebClient as SlackClient
from starlette.requests import Request
from temporalio.client import Client as TemporalClient

from pydantic_temporal_example.config import get_settings
from pydantic_temporal_example.temporal.client import build_temporal_client


@asynccontextmanager
async def lifespan(_server: FastAPI) -> AsyncIterator[dict[str, Any]]:
    """Initialize shared app state (Temporal client, Slack bot user id) for FastAPI lifespan."""
    logger = logging.getLogger(__name__)
    settings = get_settings()
    slack_client: SlackClient | None = None
    temporal_client: TemporalClient | None = None

    try:
        # Initialize Slack client
        slack_client = SlackClient(token=settings.slack_bot_token.get_secret_value(), timeout=60)

        try:
            slack_bot_user_id: str = cast("str", (await slack_client.auth_test())["user_id"])  # pyright: ignore[reportUnknownMemberType]
        except Exception as e:
            logger.exception(f"Failed to authenticate Slack client: {e}")
            raise

        # Initialize Temporal client
        try:
            temporal_client = await build_temporal_client()
        except Exception as e:
            logger.exception(f"Failed to build Temporal client: {e}")
            raise

        try:
            yield {"temporal_client": temporal_client, "slack_bot_user_id": slack_bot_user_id}
        finally:
            # Cleanup: close both clients
            if temporal_client is not None:
                try:
                    await temporal_client.close()
                    logger.info("Temporal client closed successfully")
                except Exception as e:
                    logger.exception(f"Error closing Temporal client: {e}")

            if slack_client is not None:
                try:
                    await slack_client.close()
                    logger.info("Slack client closed successfully")
                except Exception as e:
                    logger.exception(f"Error closing Slack client: {e}")
    except Exception:
        # If initialization failed, still attempt cleanup
        if temporal_client is not None:
            try:
                await temporal_client.close()
            except Exception as e:
                logger.exception(f"Error closing Temporal client during error handling: {e}")

        if slack_client is not None:
            try:
                await slack_client.close()
            except Exception as e:
                logger.exception(f"Error closing Slack client during error handling: {e}")
        raise


async def get_temporal_client(request: Request) -> TemporalClient:
    """Return the Temporal client injected in request state by the lifespan handler."""
    return request.state.temporal_client


async def get_slack_bot_user_id(request: Request) -> str:
    """Return the Slack bot user id injected in request state by the lifespan handler."""
    return request.state.slack_bot_user_id
