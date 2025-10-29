"""FastAPI app setup and local dev entrypoint with Temporal worker."""

import logfire
import uvicorn
import uvloop
from fastapi import FastAPI

from pydantic_temporal_example.api import router
from pydantic_temporal_example.dependencies import lifespan
from pydantic_temporal_example.temporal.worker import temporal_worker

# Configure logfire once at module level (before app creation)
logfire.configure(console=None)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)

app = FastAPI(lifespan=lifespan)
app.include_router(router)

logfire.instrument_fastapi(app)


async def main() -> None:
    """FastAPI app setup and local dev entrypoint with Temporal worker."""
    # Optional: install uvloop (no-op on Windows)

    async with temporal_worker():
        host = "127.0.0.1"  # Use localhost instead of binding to all interfaces
        port = 4000
        config = uvicorn.Config("pydantic_temporal_example.app:app", host=host, port=port)
        server = uvicorn.Server(config)
        await server.serve()


if __name__ == "__main__":
    uvloop.run(main())
