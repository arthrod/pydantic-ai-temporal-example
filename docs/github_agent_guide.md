# GitHub Agent Guide

## Overview

The GitHub Agent is a pydantic_ai-powered agent that can analyze GitHub repositories, pull requests, and code structure. It follows the pydantic_ai agent pattern with dependencies and tools.

## Architecture

### Components

1. **GitHubConn** (`src/pydantic_temporal_example/tools/pygithub.py`)
   - Connection wrapper for PyGithub library
   - Handles authentication and API calls
   - Uses organization from config

2. **GitHubAgent** (`src/pydantic_temporal_example/agents/github_agent.py`)
   - Main agent implementation
   - Defines tools for repository analysis
   - Returns structured responses

### Agent Structure

Following the pydantic_ai pattern:

```python
@dataclass
class GitHubDependencies:
    """Dependencies injected into the agent context"""
    repo_name: str
    db: GitHubConn

class GitHubResponse(BaseModel):
    """Structured output from the agent"""
    response: str
    repo_analyzed: str
    risk_level: int = 0

github_agent = Agent(
    'openai:gpt-4o',
    deps_type=GitHubDependencies,
    output_type=GitHubResponse,
    instructions="..."
)
```

## Available Tools

The agent provides the following tools:

### 1. view_repo_files
View files and directories in the repository at a specified path.

**Parameters:**
- `path` (str): Path within the repository (default: root)

**Example:**
```python
"Show me the files in the src directory"
```

### 2. view_pull_request
View details of a specific pull request.

**Parameters:**
- `pr_number` (int): Pull request number

**Example:**
```python
"Show me details of PR #42"
```

### 3. view_pr_comments
View all comments on a pull request (both issue comments and review comments).

**Parameters:**
- `pr_number` (int): Pull request number

**Example:**
```python
"What are the comments on PR #42?"
```

### 4. view_branches
View all branches in the repository with protection status.

**Example:**
```python
"List all branches in this repo"
```

## Configuration

Set the following environment variables in your `.env` file:

```bash
GITHUB_PAT=your_github_personal_access_token
GITHUB_ORG=your_organization_name
```

## Usage Example

```python
from pydantic_temporal_example.agents.github_agent import (
    github_agent,
    GitHubDependencies
)
from pydantic_temporal_example.tools.pygithub import GitHubConn

# Initialize dependencies
deps = GitHubDependencies(
    repo_name='pydantic-ai-temporal-example',
    db=GitHubConn()
)

# Run synchronously
result = github_agent.run_sync(
    'Show me the branches in this repository',
    deps=deps
)

print(result.output)
# GitHubResponse(
#     response='The repository has the following branches: ...',
#     repo_analyzed='pydantic-ai-temporal-example',
#     risk_level=1
# )

# Run asynchronously
result = await github_agent.run(
    'What changed in PR #15?',
    deps=deps
)
```

## Integration with Temporal

The agent is designed to integrate with the Temporal workflow orchestration:

1. **Dispatch Agent** routes GitHub-related queries to the GitHub agent
2. **GitHubRequest** dataclass carries the query and context
3. Agent executes with injected dependencies
4. Returns structured **GitHubResponse**

## Authentication

The agent uses PyGithub with token authentication:

1. Personal Access Token (PAT) from `GITHUB_PAT` environment variable
2. Organization name from `GITHUB_ORG` environment variable
3. Only repo name needs to be provided (organization is automatic)

## Example Queries

- "Show me the files in the root directory"
- "What are the details of PR #42?"
- "List all comments on PR #15"
- "Show me all branches"
- "What files are in the src/agents directory?"

## Error Handling

The GitHubConn class will raise exceptions if:
- Repository not found
- Pull request doesn't exist
- Invalid path specified
- Authentication fails

These exceptions should be caught and handled by the calling code.
