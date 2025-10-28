import pytest
import pydantic_temporal_example.temporal.github_activities as ga
from pydantic_temporal_example.agents.github_agent import GitHubResponse


class FakeGitHubAgent:
    async def github_agent_run(self, query, _deps):
        return GitHubResponse(response=f"Ran: {query}")


@pytest.mark.asyncio
async def test_fetch_github_prs_monkeypatched(monkeypatch):
    monkeypatch.setattr(ga, "GitHubAgent", lambda: FakeGitHubAgent(), raising=True)
    res = await ga.fetch_github_prs("repo", "List all pull requests in the repository")
    assert isinstance(res, GitHubResponse)
    assert "List all pull requests" in res.response