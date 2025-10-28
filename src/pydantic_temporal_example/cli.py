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
import uvloop

from pydantic_temporal_example.temporal.worker import temporal_worker

app = typer.Typer()


@app.command()
def github_prs(
    repo: Annotated[str, typer.Option(help='Repository name')] = 'potion',
    query: Annotated[
        str, typer.Option(help='Query for the GitHub agent')
    ] = 'List all pull requests in the repository',
):
    """Query GitHub agent for all PRs once using Temporal activity."""
    from pydantic_temporal_example.temporal.github_activities import fetch_github_prs

    async def _run():
        logfire.info(f'Fetching all PRs from {repo}...')
        logfire.info(f'Query: {query}')

        try:
            result = await fetch_github_prs(repo, query)

            logfire.info('GitHub Agent Response:')
            print('\n' + '=' * 80)
            print(f'GITHUB PR CHECK - Repository: {repo}')
            print('=' * 80)
            print(result.response)
            print('=' * 80)
            print(f'\nRepository analyzed: {result.repo_analyzed}')
        except Exception as e:
            logfire.error(f'Error fetching PRs: {e}')
            print(f'\nError: {e}')

    asyncio.run(_run())


@app.command()
def github_prs_periodic(
    repo: Annotated[str, typer.Option(help='Repository name')] = 'potion',
    interval: Annotated[int, typer.Option(help='Check interval in seconds')] = 30,
    query: Annotated[
        str, typer.Option(help='Query for the GitHub agent')
    ] = 'List all pull requests in the repository',
):
    """Run periodic GitHub PR checks using Temporal workflow."""
    from pydantic_temporal_example.temporal.client import build_temporal_client
    from pydantic_temporal_example.temporal.workflows import PeriodicGitHubPRCheckWorkflow

    async def _run():
        logfire.info(f'Starting periodic PR checks for {repo} every {interval}s...')
        logfire.info(f'Query: {query}')
        logfire.info('Make sure the Temporal worker is running in another terminal!')
        logfire.info('Run: python -m pydantic_temporal_example.cli main')

        try:
            # Connect to Temporal
            client = await build_temporal_client()

            # Start the workflow
            workflow_id = f'github-pr-check-{repo}'
            handle = await client.start_workflow(
                PeriodicGitHubPRCheckWorkflow.run, repo, interval, query, id=workflow_id, task_queue='agent-task-queue'
            )

            logfire.info(f'Started workflow: {workflow_id}')
            print(f'\n{"=" * 80}')
            print(f'Workflow started: {workflow_id}')
            print(f'Repository: {repo}')
            print(f'Check interval: {interval}s')
            print(f'Query: {query}')
            print(f'{"=" * 80}\n')
            print('Press Ctrl+C to stop...')

            # Wait for workflow (or Ctrl+C)
            try:
                await handle.result()
            except KeyboardInterrupt:
                logfire.info('Stopping workflow...')
                await handle.signal(PeriodicGitHubPRCheckWorkflow.stop)
                print('\nWorkflow stopped.')

        except Exception as e:
            logfire.error(f'Error running periodic checks: {e}')
            print(f'\nError: {e}')

    asyncio.run(_run())


@app.command()
def jina_research(
    query: Annotated[str, typer.Option(help='Research query')] = 'pydantic_ai',
    interval: Annotated[int, typer.Option(help='Interval in seconds')] = 30,
    iterations: Annotated[int, typer.Option(help='Number of iterations (0 = infinite)')] = 0,
):
    """Run periodic Jina research on a topic."""
    from pydantic_temporal_example.tools.jina_search import jina_search

    async def _run():
        count = 0
        while True:
            count += 1
            if iterations > 0 and count > iterations:
                break

            logfire.info(f"Research iteration {count}: Searching for '{query}'...")

            try:
                results = await jina_search(query, max_results=5)
                logfire.info(f'Found {len(results)} results')

                print(f'\n{"=" * 80}')
                print(f'Research #{count} - Query: {query}')
                print(f'{"=" * 80}')
                for i, result in enumerate(results, 1):
                    print(f'\n{i}. {result.get("title", "No title")}')
                    print(f'   URL: {result.get("url", "N/A")}')
                    if 'description' in result:
                        desc = result['description'][:200]
                        print(f'   {desc}...')
                print(f'{"=" * 80}\n')

            except Exception as e:
                logfire.error(f'Error during research: {e}')

            if iterations == 0 or count < iterations:
                logfire.info(f'Waiting {interval} seconds before next iteration...')
                await asyncio.sleep(interval)

    asyncio.run(_run())


@app.command()
def combined_task(
    repo: Annotated[str, typer.Option(help='Repository name')] = 'pydantic-ai-temporal-example',
    research_query: Annotated[str, typer.Option(help='Jina research query')] = 'pydantic_ai',
    research_interval: Annotated[int, typer.Option(help='Research interval in seconds')] = 30,
):
    """Run both GitHub PR analysis and periodic Jina research concurrently."""
    from pydantic_temporal_example.agents.github_agent import GitHubDependencies, github_agent_wrapper
    from pydantic_temporal_example.tools.jina_search import jina_search
    from pydantic_temporal_example.tools.pygithub import GitHubConn

    async def github_task():
        deps = GitHubDependencies(repo_name=repo, db=GitHubConn())

        logfire.info(f'Fetching all PRs from {repo}...')
        result = await github_agent_wrapper.run(
            'List all pull requests in the repository and include their comments for each PR', deps=deps
        )

        print('\n' + '=' * 80)
        print('GITHUB PR ANALYSIS')
        print('=' * 80)
        print(result.response)
        print('=' * 80)
        print(f'Repository analyzed: {result.repo_analyzed}\n')

    async def jina_task():
        count = 0
        while True:
            count += 1
            logfire.info(f"Jina research iteration {count}: '{research_query}'...")

            try:
                results = await jina_search(research_query, max_results=5)

                print(f'\n{"=" * 80}')
                print(f'JINA RESEARCH #{count} - Query: {research_query}')
                print(f'{"=" * 80}')
                for i, result in enumerate(results, 1):
                    print(f'{i}. {result.get("title", "No title")}')
                    print(f'   {result.get("url", "N/A")}')
                print(f'{"=" * 80}\n')

            except Exception as e:
                logfire.error(f'Jina research error: {e}')

            await asyncio.sleep(research_interval)

    async def _run():
        # Run GitHub task once, then start Jina research loop
        await github_task()
        await jina_task()

    asyncio.run(_run())


app_typer = app


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

    uvloop.run(_main())


if __name__ == "__main__":
    app()
