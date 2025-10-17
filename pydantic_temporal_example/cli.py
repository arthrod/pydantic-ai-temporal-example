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
    ] = get_settings().temporal_host,
    port: Annotated[
        int,
        typer.Option(
            help="The port for the temporal worker.",
        ),
    ] = get_settings().temporal_port,
    task_queue: Annotated[
        str,
        typer.Option(
            help="The task queue for the temporal worker.",
        ),
    ] = get_settings().temporal_task_queue,
):
    """Temporal Agent CLI"""

    async def _main():
        async with temporal_worker(
            host=host,
            port=port,
            task_queue=task_queue,
        ):
            print("Temporal worker started, press Ctrl+C to exit.")
            await asyncio.Future()

    asyncio.run(_main())


if __name__ == "__main__":
    app()
