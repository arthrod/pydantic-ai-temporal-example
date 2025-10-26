"""CLI entry point for the Temporal worker agent.

Provides a command-line interface to start the Temporal worker with configurable
host, port, and task queue options.
"""

import asyncio
import signal
import sys
from typing import Annotated

import logfire
import typer

try:
    import uvloop  # pyright: ignore[reportMissingImports]

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
except ImportError:
    logfire.warn("uvloop not available, using default event loop")

from pydantic_temporal_example.config import get_settings
from pydantic_temporal_example.temporal.worker import temporal_worker

app = typer.Typer()


@app.command()
def main(
    host: Annotated[
        str | None,
        typer.Option(
            help="The host for the temporal worker.",
        ),
    ] = None,
    port: Annotated[
        int | None,
        typer.Option(
            help="The port for the temporal worker.",
        ),
    ] = None,
    task_queue: Annotated[
        str | None,
        typer.Option(
            help="The task queue for the temporal worker.",
        ),
    ] = None,
):
    """Temporal Agent CLI."""
    # Resolve settings at runtime, not at import time
    settings = get_settings()
    host = host or settings.temporal_host
    port = port or settings.temporal_port
    task_queue = task_queue or settings.temporal_task_queue

    async def _main():
        try:
            async with temporal_worker(
                host=host,
                port=port,
                task_queue=task_queue,
            ):
                logfire.info(
                    "Temporal worker started",
                    host=host,
                    port=port,
                    task_queue=task_queue,
                )

                # Set up graceful shutdown
                shutdown_event = asyncio.Event()

                def signal_handler(sig: int, frame: object) -> None:
                    logfire.info("Received shutdown signal, stopping worker...")
                    shutdown_event.set()

                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)

                await shutdown_event.wait()
                logfire.info("Worker stopped")
        except Exception as e:
            logfire.exception(f"Worker failed: {e}")
            sys.exit(1)

    asyncio.run(_main())


if __name__ == "__main__":
    app()
