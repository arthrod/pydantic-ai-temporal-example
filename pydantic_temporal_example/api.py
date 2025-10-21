"""FastAPI routes handling Slack Events API and Temporal workflow orchestration."""

from __future__ import annotations

from typing import Annotated, Any, assert_never

import logfire
from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse, Response
from temporalio.exceptions import TemporalError

from pydantic_temporal_example.dependencies import TemporalClient, get_slack_bot_user_id, get_temporal_client
from pydantic_temporal_example.models import (
    AppMentionEvent,
    MessageChannelsEvent,
    SlackEventsAPIBody,
    URLVerificationEvent,
)
from pydantic_temporal_example.settings import get_settings
from pydantic_temporal_example.slack import get_verified_slack_events_body
from pydantic_temporal_example.temporal.workflows import SlackThreadWorkflow

router = APIRouter()


@router.post("/slack-events")
async def handle_event(
    *,
    temporal_client: Annotated[TemporalClient, Depends(get_temporal_client)],
    slack_bot_user_id: Annotated[str, Depends(get_slack_bot_user_id)],
    body: Annotated[
        SlackEventsAPIBody | URLVerificationEvent | dict[str, Any],
        Depends(get_verified_slack_events_body),
    ],
) -> Response:
    """This should be used as the endpoint for the Slack Events API for your bot."""
    if isinstance(body, dict):
        logfire.warn("Unhandled Slack event", body=body)
    elif isinstance(body, URLVerificationEvent):
        return await handle_url_verification_event(body)
    elif isinstance(body, SlackEventsAPIBody):
        if isinstance(body.event, AppMentionEvent):
            return await handle_app_mention_event(body.event, temporal_client)
        if isinstance(body.event, MessageChannelsEvent):
            if body.event.user == slack_bot_user_id:
                logfire.info("Ignoring event for message created by this bot")
            else:
                return await handle_message_channels_event(body.event, temporal_client)
        else:
            assert_never(body.event)
    else:
        assert_never(body)

    return Response(status_code=204)


async def handle_url_verification_event(event: URLVerificationEvent) -> JSONResponse:
    """Return Slack URL verification challenge back to Slack."""
    return JSONResponse(content={"challenge": event.challenge})


async def handle_app_mention_event(event: AppMentionEvent, temporal_client: TemporalClient) -> Response:
    """Start a workflow for a Slack thread when the bot is app-mentioned."""
    settings = get_settings()
    workflow_id = f"app-mention-{event.reply_thread_ts.replace('.', '-')}"
    await temporal_client.start_workflow(
        SlackThreadWorkflow.run,
        id=workflow_id,
        start_signal="submit_app_mention_event",
        start_signal_args=[event],
        task_queue=settings.temporal_task_queue,
    )
    return Response(status_code=204)


async def handle_message_channels_event(event: MessageChannelsEvent, temporal_client: TemporalClient) -> Response:
    """Signal an existing workflow with a new message or ignore if none exists yet."""
    maybe_workflow_id = f"app-mention-{event.reply_thread_ts.replace('.', '-')}"
    maybe_handle = temporal_client.get_workflow_handle_for(SlackThreadWorkflow.run, workflow_id=maybe_workflow_id)
    try:
        await maybe_handle.describe()
        await maybe_handle.signal("submit_message_channels_event", args=[event])
    except TemporalError:
        # workflow doesn't exist yet, do nothing other than record what happened
        logfire.info("No workflow found for this thread")
    return Response(status_code=204)
