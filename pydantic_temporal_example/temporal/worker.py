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
async def temporal_worker(
    host: str | None = None,
    port: int | None = None,
    task_queue: str | None = None,
) -> AsyncIterator[Worker]:
    """Start a Temporal worker as an async context manager.

    Args:
        host: Temporal server host. If None, starts local test environment. Defaults to settings or None.
        port: Temporal server port. Defaults to settings or 7233.
        task_queue: Task queue name. Defaults to settings or "agent-task-queue".

    Yields:
        Worker: Configured and running Temporal worker instance.

    Raises:
        ValueError: If port is out of valid range (1-65535) or task_queue is empty.
    """
    settings = get_settings()
    host = host or settings.temporal_host
    resolved_port = port or settings.temporal_port
    task_queue = task_queue or settings.temporal_task_queue

    # Note: resolved_port will always have a value from settings.temporal_port default (7233)
    # Port validation is already enforced in Settings model via Field constraints

    # Validate task_queue
    if not task_queue or not task_queue.strip():
        raise ValueError("task_queue cannot be empty")

    async with AsyncExitStack() as stack:
        if host is None:
            workflow_env = await WorkflowEnvironment.start_local(port=resolved_port, ui=True)  # pyright: ignore[reportUnknownMemberType]
            await stack.enter_async_context(workflow_env)

        client = await build_temporal_client(host=host, port=resolved_port)
        worker = await stack.enter_async_context(
            Worker(
                client,
                task_queue=task_queue,
                workflows=[SlackThreadWorkflow],
                activities=ALL_SLACK_ACTIVITIES,
                plugins=[
                    AgentPlugin(temporal_dispatch_agent),
                    AgentPlugin(TemporalAgent(build_web_research_agent(), name="web_research_agent")),
                    AgentPlugin(temporal_github_agent),
                ],
            ),
        )
        yield worker
