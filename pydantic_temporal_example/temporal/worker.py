from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from pydantic_ai.durable_exec.temporal import AgentPlugin
from temporalio.worker import Worker

from pydantic_temporal_example.config import get_settings
from pydantic_temporal_example.temporal.client import build_temporal_client
from pydantic_temporal_example.temporal.slack_activities import ALL_SLACK_ACTIVITIES
from pydantic_temporal_example.temporal.workflows import (
    SlackThreadWorkflow,
    temporal_dinner_research_agent,
    temporal_dispatch_agent,
)


@asynccontextmanager
async def temporal_worker(
    host: str | None = None,
    port: int | None = None,
    task_queue: str | None = None,
) -> AsyncIterator[Worker]:
    settings = get_settings()
    host = host or settings.temporal_host
    port = port or settings.temporal_port
    task_queue = task_queue or settings.temporal_task_queue

    async with AsyncExitStack() as stack:
        if host is None:
            from temporalio.testing import WorkflowEnvironment

            workflow_env = await WorkflowEnvironment.start_local(port=port, ui=True)  # pyright: ignore[reportUnknownMemberType]
            await stack.enter_async_context(workflow_env)

        client = await build_temporal_client(host=host, port=port)
        worker = await stack.enter_async_context(
            Worker(
                client,
                task_queue=task_queue,
                workflows=[SlackThreadWorkflow],
                activities=ALL_SLACK_ACTIVITIES,
                plugins=[
                    AgentPlugin(temporal_dispatch_agent),
                    AgentPlugin(temporal_dinner_research_agent),
                ],
            )
        )
        yield worker
