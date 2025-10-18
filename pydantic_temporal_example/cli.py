import asyncio
from typing import Annotated

import typer

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
) -> None:
    """Temporal Agent CLI"""
    settings = get_settings()
    host = host or settings.temporal_host
    port = port or settings.temporal_port
    task_queue = task_queue or settings.temporal_task_queue

    async def _main() -> None:
        async with temporal_worker(
            host=host,
            port=port,
            task_queue=task_queue,
        ) as worker:
            print("Temporal worker started. Press Ctrl+C to exit.")
            await worker.run()
            print("Temporal worker finished.")

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    app()
