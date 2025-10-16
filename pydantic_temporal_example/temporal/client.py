import logfire
from pydantic_ai.durable_exec.temporal import LogfirePlugin, PydanticAIPlugin
from temporalio.client import Client as TemporalClient

from pydantic_temporal_example.config import get_settings


async def build_temporal_client(host: str | None = None, port: int | None = None) -> TemporalClient:
    settings = get_settings()
    host = host or settings.temporal_host or "localhost"
    port = port or settings.temporal_port

    def _setup_logfire() -> logfire.Logfire:
        instance = logfire.configure()
        logfire.instrument_pydantic_ai()
        logfire.instrument_httpx(capture_all=True)
        return instance

    return await TemporalClient.connect(f"{host}:{port}", plugins=[PydanticAIPlugin(), LogfirePlugin(_setup_logfire)])
