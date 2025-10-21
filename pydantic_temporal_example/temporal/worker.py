"""Temporal worker setup orchestrating workflows and agent plugins for dev."""

from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING

from pydantic_ai.durable_exec.temporal import AgentPlugin, TemporalAgent
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from pydantic_temporal_example.agents.web_research_agent import build_web_research_agent
from pydantic_temporal_example.settings import get_settings
from pydantic_temporal_example.temporal.client import build_temporal_client
from pydantic_temporal_example.temporal.slack_activities import ALL_SLACK_ACTIVITIES
from pydantic_temporal_example.temporal.workflows import (
    SlackThreadWorkflow,
    temporal_dispatch_agent,
    temporal_github_agent,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def temporal_worker() -> AsyncIterator[Worker]:
    """Start a Temporal worker and required local environment, yielding it for app lifetime."""
    settings = get_settings()
    async with AsyncExitStack() as stack:
        if settings.temporal_host is None:
            workflow_env = await WorkflowEnvironment.start_local(port=settings.temporal_port, ui=True)  # pyright: ignore[reportUnknownMemberType]
            await stack.enter_async_context(workflow_env)

        client = await build_temporal_client()
        yield await stack.enter_async_context(
            Worker(
                client,
                task_queue=settings.temporal_task_queue,
                workflows=[SlackThreadWorkflow],
                activities=ALL_SLACK_ACTIVITIES,
                plugins=[
                    AgentPlugin(temporal_dispatch_agent),
                    AgentPlugin(TemporalAgent(build_web_research_agent(), name="web_research_agent")),
                    AgentPlugin(temporal_github_agent),
                ],
            ),
        )
