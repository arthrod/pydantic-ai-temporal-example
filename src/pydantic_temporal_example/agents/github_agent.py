"""GitHub-focused agent returning structured responses for repository and issue tasks."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai_claude_code import ClaudeCodeProvider

from pydantic_temporal_example.tools.pygithub import GitHubConn

provider = ClaudeCodeProvider({'use_sandbox_runtime': False})


class GitHubDependencies(BaseModel):
    """Dependencies for the GitHub agent."""

    repo_name: str = Field(
        ..., description='The name of the GitHub repository to operate on (without organization prefix).'
    )
    db: GitHubConn = Field(..., description='The GitHub connection instance for making API calls.')

    @field_validator('repo_name')
    @classmethod
    def validate_repo_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Repository name cannot be empty')
        if not v.replace('-', '').replace('_', '').isalnum():
            # Basic validation - repo names can contain alphanumeric characters, hyphens, and underscores
            raise ValueError('Repository name contains invalid characters')
        return v.strip()


class GitHubResponse(BaseModel):
    """Structured output produced by the GitHub agent."""

    response: str
    """The formatted message to show to the user."""
    repo_analyzed: str
    """The repository that was analyzed."""


class GitHubAgent(BaseModel):
    """GitHub agent that helps users understand repositories, pull requests, and code structure."""

    deps: GitHubDependencies
    response: GitHubResponse
    self.github = Agent(
    model=GITHUB_AGENT_MODEL,
    deps_type=GitHubDependencies,
    output_type=GitHubResponse,
    system_prompt=(
        'You are a GitHub analysis agent that helps users understand '
        'repositories, pull requests, and code structure. '
        'Provide clear, informative responses based on the repository data.'
    ),
)


github_agent = 


@github_agent.tool
async def view_repo_files(ctx: RunContext[GitHubDependencies], path: str = '') -> str:
    """View files in the repository at the specified path.

    Args:
        ctx: Runtime context with dependencies
        path: Path within the repository (default: root)

    Returns:
        Formatted string listing the files and directories
    """
    files = ctx.deps.db.get_repo_files(ctx.deps.repo_name, path)
    result = [f'Files in {ctx.deps.repo_name}/{path or "root"}:']
    for file in files:
        file_type = '📁' if file.type == 'dir' else '📄'
        result.append(f'{file_type} {file.path}')
    return '\n'.join(result)


@github_agent.tool
async def view_pull_request(ctx: RunContext[GitHubDependencies], pr_number: int) -> str:
    """View details of a specific pull request.

    Args:
        ctx: Runtime context with dependencies
        pr_number: Pull request number

    Returns:
        Formatted string with PR details
    """
    pr = ctx.deps.db.get_pull_request(ctx.deps.repo_name, pr_number)
    return (
        f'Pull Request #{pr.number}: {pr.title}\n'
        f'State: {pr.state}\n'
        f'Author: {pr.user.login}\n'
        f'Created: {pr.created_at}\n'
        f'Description: {pr.body or "No description"}\n'
        f'Changed Files: {pr.changed_files}\n'
        f'Additions: +{pr.additions} | Deletions: -{pr.deletions}'
    )


@github_agent.tool
async def view_pr_comments(ctx: RunContext[GitHubDependencies], pr_number: int) -> str:
    """View all comments on a pull request.

    Args:
        ctx: Runtime context with dependencies
        pr_number: Pull request number

    Returns:
        Formatted string with all comments
    """
    comments = ctx.deps.db.get_pr_comments(ctx.deps.repo_name, pr_number)
    if not comments:
        return f'No comments found on PR #{pr_number}'

    result = [f'Comments on PR #{pr_number}:']
    for comment in comments:
        comment_type = '💬' if comment['type'] == 'issue_comment' else '📝'
        result.append(f'\n{comment_type} {comment["user"]} ({comment["created_at"]}):\n{comment["body"]}')
        if 'path' in comment:
            result.append(f'  File: {comment["path"]}')

    return '\n'.join(result)


@github_agent.tool
async def view_branches(ctx: RunContext[GitHubDependencies]) -> str:
    """View all branches in the repository.

    Args:
        ctx: Runtime context with dependencies

    Returns:
        Formatted string listing all branches
    """
    branches = ctx.deps.db.get_branches(ctx.deps.repo_name)
    result = [f'Branches in {ctx.deps.repo_name}:']
    for branch in branches:
        protected = '🔒' if branch['protected'] else '🔓'
        result.append(f'{protected} {branch["name"]} ({branch["sha"][:7]})')
    return '\n'.join(result)


if __name__ == '__main__':
    # Example usage (requires GITHUB_PAT and GITHUB_ORG environment variables)
    try:
        deps = GitHubDependencies(repo_name='pydantic-ai-temporal-example', db=GitHubConn())
        result = github_agent.run_sync('Show me the branches in this repository', deps=deps)
        print(result.output)
    except Exception as e:
        print(f"Error running GitHub agent: {str(e)}")
    """
    Example output:
    response='The repository has the following branches: main (protected), develop (not protected), ...'
    repo_analyzed='pydantic-ai-temporal-example'
    risk_level=1
    """
