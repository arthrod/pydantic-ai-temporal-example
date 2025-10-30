"""FastAPI routes handling Slack Events API and Temporal workflow orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, assert_never

import logfire
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, Response
from temporalio.exceptions import TemporalError

from pydantic_temporal_example.config import get_settings
from pydantic_temporal_example.dependencies import TemporalClient, get_slack_bot_user_id, get_temporal_client
from pydantic_temporal_example.models import (
    AppMentionEvent,
    CLIPromptEvent,
    MessageChannelsEvent,
    SlackEventsAPIBody,
    URLVerificationEvent,
)
from pydantic_temporal_example.temporal.workflows import (
    CLIConversationWorkflow,
    SlackThreadWorkflow,
)
from pydantic_temporal_example.tools.slack import get_verified_slack_events_body

router = APIRouter()


@router.post("/slack-events")
async def handle_event(
    *,
    temporal_client: Annotated[TemporalClient, Depends(get_temporal_client)],
    slack_bot_user_id: Annotated[str | None, Depends(get_slack_bot_user_id)],
    body: Annotated[
        SlackEventsAPIBody | URLVerificationEvent | dict[str, Any],
        Depends(get_verified_slack_events_body),
    ],
) -> Response:
    """This should be used as the endpoint for the Slack Events API for your bot."""
    if isinstance(body, dict):
        logfire.warning("Unhandled Slack event", body=body)
    elif isinstance(body, URLVerificationEvent):
        return await handle_url_verification_event(body)
    elif isinstance(body, SlackEventsAPIBody):
        if isinstance(body.event, AppMentionEvent):
            return await handle_app_mention_event(body.event, temporal_client)
        if isinstance(body.event, MessageChannelsEvent):
            if slack_bot_user_id and body.event.user == slack_bot_user_id:
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


# CLI Request/Response Models
class CLIWorkflowRequest(BaseModel):
    """Request model for CLI workflow submission."""

    prompt: str = Field(..., description="The prompt/command to execute")
    session_id: str | None = Field(None, description="Optional session identifier")
    repeat: bool = Field(False, description="Whether to repeat the command periodically")
    repeat_interval: int = Field(30, description="Interval in seconds for repetition", ge=1)
    repo_name: str = Field("default-repo", description="Repository name for GitHub operations")


class CLIWorkflowAssignmentResponse(BaseModel):
    """Response model for workflow assignment confirmation."""

    success: bool = Field(..., description="Whether the workflow was assigned successfully")
    workflow_id: str = Field(..., description="ID of the assigned workflow")
    message: str = Field(..., description="Human-readable message")
    is_repeating: bool = Field(False, description="Whether this is a repeating workflow")


@router.post("/cli-workflow")
async def submit_cli_workflow(
    *,
    temporal_client: Annotated[TemporalClient, Depends(get_temporal_client)],
    request: CLIWorkflowRequest,
) -> JSONResponse:
    """Submit a CLI workflow and return assignment confirmation."""
    try:
        # Generate unique workflow ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        workflow_id = f"cli-workflow-{timestamp}-{hash(request.prompt) % 10000:04d}"

        # Create CLI prompt event
        cli_event = CLIPromptEvent(
            prompt=request.prompt,
            timestamp=datetime.now().isoformat(),
            session_id=request.session_id,
        )

        # Start the CLI conversation workflow
        await temporal_client.start_workflow(
            CLIConversationWorkflow.run,
            id=workflow_id,
            start_signal="submit_prompt",
            start_signal_args=[cli_event],
            task_queue=get_settings().temporal_task_queue,
        )

        # If repeat is requested, start a periodic workflow
        if request.repeat:
            periodic_workflow_id = f"periodic-cli-{workflow_id}"
            from pydantic_temporal_example.temporal.workflows import PeriodicGitHubPRCheckWorkflow

            await temporal_client.start_workflow(
                PeriodicGitHubPRCheckWorkflow.periodic_run,
                args=[request.repo_name, request.repeat_interval, request.prompt],
                id=periodic_workflow_id,
                task_queue=get_settings().temporal_task_queue,
            )

            response = CLIWorkflowAssignmentResponse(
                success=True,
                workflow_id=f"{workflow_id},{periodic_workflow_id}",
                message="Workflow assigned to worker. (Repeating mode enabled)",
                is_repeating=True,
            )
        else:
            response = CLIWorkflowAssignmentResponse(
                success=True,
                workflow_id=workflow_id,
                message="Workflow assigned to a worker.",
                is_repeating=False,
            )

        logfire.info("CLI workflow submitted", workflow_id=response.workflow_id, prompt=request.prompt)
        return JSONResponse(content=response.model_dump())

    except Exception as e:
        logfire.error("Failed to submit CLI workflow", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to assign workflow to worker")


@router.get("/cli-workflow/{workflow_id}/response")
async def get_cli_workflow_response(
    *,
    temporal_client: Annotated[TemporalClient, Depends(get_temporal_client)],
    workflow_id: str,
) -> JSONResponse:
    """Retrieve the latest response from a CLI workflow."""
    try:
        handle = temporal_client.get_workflow_handle_for(CLIConversationWorkflow.run, workflow_id=workflow_id)

        # Query for the latest response
        response = await handle.query(CLIConversationWorkflow.get_latest_response)

        if response is None:
            return JSONResponse(content={"status": "pending", "response": None})

        return JSONResponse(content={"status": "completed", "response": response.model_dump()})

    except TemporalError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except Exception as e:
        logfire.error("Failed to query CLI workflow response", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve workflow response")


@router.delete("/cli-workflow/{workflow_id}")
async def stop_cli_workflow(
    *,
    temporal_client: Annotated[TemporalClient, Depends(get_temporal_client)],
    workflow_id: str,
) -> JSONResponse:
    """Stop a running CLI workflow."""
    try:
        # Try to stop as CLI conversation workflow first
        try:
            handle = temporal_client.get_workflow_handle_for(CLIConversationWorkflow.run, workflow_id=workflow_id)
            await handle.signal("stop")
            logfire.info("CLI workflow stopped", workflow_id=workflow_id)
            return JSONResponse(content={"success": True, "message": "Workflow stopped successfully"})
        except TemporalError:
            pass

        # Try to stop as periodic workflow
        try:
            from pydantic_temporal_example.temporal.workflows import PeriodicGitHubPRCheckWorkflow

            handle = temporal_client.get_workflow_handle_for(
                PeriodicGitHubPRCheckWorkflow.periodic_run,
                workflow_id=workflow_id,
            )
            await handle.signal(PeriodicGitHubPRCheckWorkflow.stop)
            logfire.info("Periodic workflow stopped", workflow_id=workflow_id)
            return JSONResponse(content={"success": True, "message": "Periodic workflow stopped successfully"})
        except TemporalError:
            pass

        raise HTTPException(status_code=404, detail="Workflow not found or already stopped")

    except Exception as e:
        logfire.error("Failed to stop CLI workflow", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to stop workflow")
