"""PyGithub wrapper for accessing GitHub repositories and pull requests."""

from typing import Any

import logfire
from github import Auth, Github
from github.ContentFile import ContentFile
from github.PullRequest import PullRequest
from github.Repository import Repository

from pydantic_temporal_example.config import get_github_org, get_github_pat


class GitHubConn:
    """GitHub connection wrapper for accessing repository information.

    This class provides methods to interact with GitHub repositories
    using the PyGithub library.
    """

    def __init__(self, organization: str | None = None) -> None:
        """Initialize GitHub connection with authentication.

        Args:
            organization: GitHub organization name (defaults to GITHUB_ORG from config)
        """
        auth = Auth.Token(get_github_pat())
        self.g = Github(auth=auth)
        self.organization = organization or get_github_org()

    def get_repo(self, repo_name: str) -> Repository:
        """Get a repository by name.

        Args:
            repo_name: Repository name (without organization)

        Returns:
            Repository object

        Raises:
            ValueError: If the repository name is invalid
            github.GithubException: If the repository cannot be found or accessed
        """
        if not repo_name or not repo_name.strip():
            msg = "Repository name cannot be empty"
            raise ValueError(msg)

        full_repo_name = f"{self.organization}/{repo_name}"
        try:
            return self.g.get_repo(full_repo_name)
        except Exception as e:
            logfire.error(f"Error accessing repository {full_repo_name}: {e!s}")
            raise  # Re-raise original exception

    def get_repo_files(self, repo_name: str, path: str = "") -> list[ContentFile]:
        """Get files from a repository at the specified path.

        Args:
            repo_name: Repository name (without organization)
            path: Path within the repository (default: root)

        Returns:
            List of ContentFile objects
        """
        try:
            repo = self.get_repo(repo_name)
            contents = repo.get_contents(path)
            if isinstance(contents, list):
                return contents
            return [contents]
        except Exception as e:
            logfire.error(f"Error getting files from path '{path}' in repository {repo_name}: {e!s}")
            raise

    def get_pull_request(self, repo_name: str, pr_number: int) -> PullRequest:
        """Get a specific pull request.

        Args:
            repo_name: Repository name (without organization)
            pr_number: Pull request number

        Returns:
            PullRequest object
        """
        try:
            repo = self.get_repo(repo_name)
            return repo.get_pull(pr_number)
        except Exception as e:
            logfire.error(f"Error getting pull request #{pr_number} from repository {repo_name}: {e!s}")
            raise

    def get_pr_comments(self, repo_name: str, pr_number: int) -> list[dict[str, Any]]:
        """Get comments from a pull request.

        Args:
            repo_name: Repository name (without organization)
            pr_number: Pull request number

        Returns:
            List of comment dictionaries with user, body, and created_at
        """
        try:
            pr = self.get_pull_request(repo_name, pr_number)

            # Get issue comments (general PR comments)
            issue_comments = [
                {
                    "user": comment.user.login,
                    "body": comment.body,
                    "created_at": comment.created_at.isoformat(),
                    "type": "issue_comment",
                }
                for comment in pr.get_issue_comments()
            ]

            # Get review comments (code-specific comments)
            review_comments = [
                {
                    "user": comment.user.login,
                    "body": comment.body,
                    "created_at": comment.created_at.isoformat(),
                    "path": comment.path,
                    "type": "review_comment",
                }
                for comment in pr.get_review_comments()
            ]

            return issue_comments + review_comments
        except Exception as e:
            logfire.error(f"Error getting comments for pull request #{pr_number} from repository {repo_name}: {e!s}")
            raise

    def get_branches(self, repo_name: str) -> list[dict[str, Any]]:
        """Get all branches from a repository.

        Args:
            repo_name: Repository name (without organization)

        Returns:
            List of branch dictionaries with name and sha
        """
        try:
            repo = self.get_repo(repo_name)
            return [
                {"name": branch.name, "sha": branch.commit.sha, "protected": branch.protected}
                for branch in repo.get_branches()
            ]
        except Exception as e:
            logfire.error(f"Error getting branches from repository {repo_name}: {e!s}")
            raise

    def list_pull_requests(self, repo_name: str, state: str = "all") -> list[dict[str, Any]]:
        """List all pull requests in a repository.

        Args:
            repo_name: Repository name (without organization)
            state: PR state filter ('open', 'closed', or 'all')

        Returns:
            List of PR dictionaries with number, title, state, and author
        """
        try:
            repo = self.get_repo(repo_name)
            return [
                {
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "author": pr.user.login,
                    "created_at": pr.created_at.isoformat() if pr.created_at else "",
                    "updated_at": pr.updated_at.isoformat() if pr.updated_at else "",
                }
                for pr in repo.get_pulls(state=state)
            ]
        except Exception as e:
            logfire.error(f"Error listing pull requests from repository {repo_name}: {e!s}")
            raise
