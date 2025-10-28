# GitHub PR Check with Temporal

This guide shows how to use the GitHub agent orchestration to check PRs in a repository.

## Setup

Make sure you have the following environment variables set in your `.env` file:
- `GITHUB_PAT`: Your GitHub Personal Access Token
- `GITHUB_ORG`: Your GitHub organization (default: "arthrod")

## Usage

### 1. Single PR Check (Test First!)

Run a single check to verify everything works:

```bash
python -m pydantic_temporal_example.cli github-prs --repo potion
```

You can also customize the query/instructions for the GitHub agent:

```bash
python -m pydantic_temporal_example.cli github-prs --repo potion --query "List all pull requests in the repository"
```

This will:
- Connect to GitHub
- Pass your query to the GitHub agent
- Fetch all PRs from the "potion" repository
- Display the results once

### 2. Periodic PR Check (Every 30 Seconds)

For the periodic check, you need two terminals:

**Terminal 1 - Start the Temporal Worker:**
```bash
python -m pydantic_temporal_example.cli main
```

This starts:
- Local Temporal server (if not running)
- Temporal worker with all workflows and activities
- Temporal UI at http://localhost:8233

**Terminal 2 - Start the Periodic Check Workflow:**
```bash
python -m pydantic_temporal_example.cli github-prs-periodic --repo potion --interval 30
```

You can also customize the query:
```bash
python -m pydantic_temporal_example.cli github-prs-periodic --repo potion --interval 30 --query "List all pull requests in the repository"
```

This will:
- Start a Temporal workflow that checks PRs every 30 seconds
- Pass your custom query to the GitHub agent on each check
- Log each check with results
- Run continuously until you press Ctrl+C

## Workflow Features

The `PeriodicGitHubPRCheckWorkflow` provides:
- **Durability**: Survives crashes and restarts
- **Observability**: View workflow execution in Temporal UI
- **Control**: Stop/start via signals
- **State tracking**: Query check count at any time

## Example Output

```
================================================================================
GITHUB PR CHECK - Repository: potion
================================================================================
Pull Requests in potion (state=all):

#1: Add new feature
  State: open | Author: developer1
  Created: 2024-01-15T10:30:00Z

#2: Fix bug in authentication
  State: closed | Author: developer2
  Created: 2024-01-14T09:20:00Z
================================================================================

Repository analyzed: potion
```

## Stopping the Periodic Check

Press `Ctrl+C` in Terminal 2. The workflow will receive a stop signal and gracefully shut down.

## Monitoring

- **Temporal UI**: http://localhost:8233
- **Logfire**: Check your Logfire dashboard for detailed traces
- **Console logs**: Real-time output in both terminals
