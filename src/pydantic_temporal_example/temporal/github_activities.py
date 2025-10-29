"""Temporal activities for GitHub operations."""

from __future__ import annotations

import logfire
from temporalio import activity

from pydantic_temporal_example.agents.github_agent import GitHubDependencies, GitHubResponse, github_agent


@activity.defn
async def fetch_github_prs(repo_name: str, query: str = "List all pull requests in the repository") -> GitHubResponse:
    """Fetch all pull requests from a GitHub repository.

    Args:
        repo_name: Repository name (without organization)
        query: The query/instruction to pass to the GitHub agent

    Returns:
        GitHubResponse with PR information
    """
    logfire.info(f"Fetching PRs from repository: {repo_name}")
    logfire.info(f"Query: {query}")

    try:
        deps = GitHubDependencies(repo_name=repo_name)
        result = await github_agent.run(query, deps=deps)

        logfire.info(f"Successfully fetched PRs from {repo_name}")
        return result.output

    except Exception as e:
        logfire.error(f"Error fetching PRs from {repo_name}: {e}")
        raise


# All GitHub activities
ALL_GITHUB_ACTIVITIES = [fetch_github_prs]
