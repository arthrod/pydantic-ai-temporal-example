"""FastAPI app setup and local dev entrypoint with Temporal worker."""

import logfire
import uvicorn
from fastapi import FastAPI

from pydantic_temporal_example.api import router
from pydantic_temporal_example.dependencies import lifespan
from pydantic_temporal_example.temporal.worker import temporal_worker

app = FastAPI(lifespan=lifespan)
app.include_router(router)


logfire.instrument_fastapi(app)


async def main() -> None:
    """FastAPI app setup and local dev entrypoint with Temporal worker."""
    # Optional: install uvloop (no-op on Windows)
    try:
        import uvloop  # type: ignore

        uvloop.install()
    except Exception:
        pass

    async with temporal_worker():
        host = "0.0.0.0"  # Expose to all interfaces for container access
        port = 4000
        config = uvicorn.Config("pydantic_temporal_example.app:app", host=host, port=port)
        server = uvicorn.Server(config)
        await server.serve()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
