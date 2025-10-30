"""Temporal client builder with Logfire and PydanticAI plugins."""

from pydantic_ai.durable_exec.temporal import LogfirePlugin, PydanticAIPlugin
from temporalio.client import Client as TemporalClient

from pydantic_temporal_example.config import get_settings


async def build_temporal_client(host: str | None = None, port: int | None = None) -> TemporalClient:
    """Build and connect a Temporal client with configurable host and port.

    Args:
        host: Temporal server host. Falls back to settings.temporal_host or "localhost"
        port: Temporal server port. Falls back to settings.temporal_port (7233)

    Returns:
        Connected TemporalClient instance configured with PydanticAI and Logfire plugins

    Raises:
        ValueError: If port is None after resolution from settings
    """
    settings = get_settings()
    temporal_host = host or settings.temporal_host or "localhost"
    temporal_port = port or settings.temporal_port
    # Note: temporal_port will always have a value from settings.temporal_port default (7233)

    return await TemporalClient.connect(
        f"{temporal_host}:{temporal_port}",
        plugins=[PydanticAIPlugin(), LogfirePlugin()],
    )
