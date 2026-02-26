"""GitHub MCP tools for Pilot Space.

These tools provide access to GitHub resources through
the GitHub integration. Requires valid GitHub integration setup.

T027: get_pr_details
T028: get_pr_diff
T029: search_code_in_repo
T032: post_pr_comment (AUTO_EXECUTE with notification)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from pilot_space.ai.tools.mcp_server import ToolContext, register_tool
from pilot_space.infrastructure.encryption import decrypt_api_key
from pilot_space.infrastructure.logging import get_logger
from pilot_space.integrations.github import GitHubClient
from pilot_space.integrations.github.exceptions import GitHubAPIError

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.integration import Integration

logger = get_logger(__name__)


async def _get_github_integration(
    ctx: ToolContext,
    integration_id: str | None = None,
) -> tuple[Integration | None, str | None]:
    """Get GitHub integration for the workspace.

    Queries the Integration table filtered by workspace and provider.
    Enforces RLS through workspace_id context.

    Args:
        ctx: Tool context with db_session and workspace_id
        integration_id: Optional specific integration ID

    Returns:
        Tuple of (integration, error_message).
        If integration found, returns (integration, None).
        If not found, returns (None, error_message).
    """
    from pilot_space.infrastructure.database.models.integration import (
        Integration,
        IntegrationProvider,
    )

    workspace_uuid = UUID(ctx.workspace_id)

    query = select(Integration).where(
        Integration.workspace_id == workspace_uuid,
        Integration.provider == IntegrationProvider.GITHUB,
        Integration.is_active.is_(True),
    )

    if integration_id:
        try:
            integration_uuid = UUID(integration_id)
            query = query.where(Integration.id == integration_uuid)
        except ValueError:
            return None, f"Invalid integration_id format: {integration_id}"

    result = await ctx.db_session.execute(query)
    integration = result.scalar_one_or_none()

    if not integration:
        if integration_id:
            return None, f"GitHub integration {integration_id} not found or inactive"
        return None, "No active GitHub integration found for this workspace"

    return integration, None


def _extract_repo_info(
    integration: Integration,
) -> tuple[str | None, str | None, str | None]:
    """Extract repository information from integration settings.

    Args:
        integration: Integration model instance

    Returns:
        Tuple of (repo_owner, repo_name, error_message).
        If successful, returns (owner, name, None).
        If failed, returns (None, None, error_message).
    """
    settings = integration.settings or {}
    default_repo = settings.get("default_repository")

    if not default_repo:
        return None, None, "GitHub integration missing default_repository in settings"

    # Parse "owner/repo" format
    parts = default_repo.split("/")
    if len(parts) != 2:
        return (
            None,
            None,
            f"Invalid repository format: {default_repo} (expected 'owner/repo')",
        )

    repo_owner, repo_name = parts
    return repo_owner, repo_name, None


@register_tool("github")
async def get_pr_details(
    pr_number: int,
    ctx: ToolContext,
    integration_id: str | None = None,
) -> dict[str, Any]:
    """Get pull request details from GitHub.

    Retrieves PR metadata including title, description,
    author, reviewers, labels, and merge status.

    Args:
        pr_number: PR number in the repository (must be positive)
        ctx: Tool context with db_session and workspace_id
        integration_id: Optional specific GitHub integration ID

    Returns:
        Dictionary with:
        - found (bool): Whether the PR was retrieved successfully
        - pr (dict): Full PR metadata
        - error (str): Error message if found=False
    """
    if pr_number <= 0:
        return {
            "error": f"Invalid PR number: {pr_number} (must be positive)",
            "found": False,
        }

    integration, error = await _get_github_integration(ctx, integration_id)

    if error:
        return {"error": error, "found": False}

    if integration is None:
        return {"error": "Integration not found", "found": False}

    repo_owner, repo_name, repo_error = _extract_repo_info(integration)

    if repo_error:
        return {"error": repo_error, "found": False}

    if repo_owner is None or repo_name is None:
        return {
            "error": "Could not determine repository owner/name from integration settings",
            "found": False,
        }

    try:
        access_token = decrypt_api_key(integration.access_token)
    except Exception:
        logger.exception("Failed to decrypt GitHub access token for integration %s", integration.id)
        return {"found": False, "error": "Failed to decrypt access token"}

    async with GitHubClient(access_token) as client:
        try:
            pr = await client.get_pull_request(repo_owner, repo_name, pr_number)
            return {
                "found": True,
                "pr": {
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body,
                    "state": pr.state,
                    "html_url": pr.html_url,
                    "merged": pr.merged,
                    "draft": pr.draft,
                    "user": {
                        "login": pr.author_login,
                        "avatar_url": pr.author_avatar_url,
                    },
                    "base": pr.base_branch,
                    "head": pr.head_branch,
                    "additions": pr.additions,
                    "deletions": pr.deletions,
                    "changed_files": pr.changed_files,
                    "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                    "labels": pr.labels,
                    "requested_reviewers": pr.requested_reviewers,
                },
            }
        except GitHubAPIError as e:
            return {"error": str(e), "found": False}


@register_tool("github")
async def get_pr_diff(
    pr_number: int,
    ctx: ToolContext,
    integration_id: str | None = None,
) -> dict[str, Any]:
    """Get full unified diff for a pull request.

    Retrieves the complete diff for code review analysis.
    Returns file-by-file changes with additions/deletions.

    Args:
        pr_number: PR number in the repository (must be positive)
        ctx: Tool context with db_session and workspace_id
        integration_id: Optional specific GitHub integration ID

    Returns:
        Dictionary with:
        - found (bool): Whether files were retrieved successfully
        - files (list): List of changed file dictionaries
        - stats (dict): Aggregate change statistics
        - error (str): Error message if found=False
    """
    if pr_number <= 0:
        return {
            "error": f"Invalid PR number: {pr_number} (must be positive)",
            "found": False,
        }

    integration, error = await _get_github_integration(ctx, integration_id)

    if error:
        return {"error": error, "found": False}

    if integration is None:
        return {"error": "Integration not found", "found": False}

    repo_owner, repo_name, repo_error = _extract_repo_info(integration)

    if repo_error:
        return {"error": repo_error, "found": False}

    if repo_owner is None or repo_name is None:
        return {
            "error": "Could not determine repository owner/name from integration settings",
            "found": False,
        }

    try:
        access_token = decrypt_api_key(integration.access_token)
    except Exception:
        logger.exception("Failed to decrypt GitHub access token for integration %s", integration.id)
        return {"found": False, "error": "Failed to decrypt access token"}

    async with GitHubClient(access_token) as client:
        try:
            pr = await client.get_pull_request(repo_owner, repo_name, pr_number)
            files = await client.get_pull_request_files(repo_owner, repo_name, pr_number)

            file_dicts = [
                {
                    "filename": f.get("filename"),
                    "status": f.get("status"),
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0),
                    "changes": f.get("changes", 0),
                    "patch": f.get("patch"),
                }
                for f in files
            ]

            return {
                "found": True,
                "files": file_dicts,
                "stats": {
                    "additions": pr.additions,
                    "deletions": pr.deletions,
                    "changed_files": pr.changed_files,
                },
            }
        except GitHubAPIError as e:
            return {"error": str(e), "found": False}


@register_tool("github")
async def search_code_in_repo(
    query: str,
    ctx: ToolContext,
    integration_id: str | None = None,
    path: str | None = None,
    extension: str | None = None,
) -> dict[str, Any]:
    """Search code in a GitHub repository.

    Uses GitHub code search API for real-time search.
    Requires GitHub integration with appropriate permissions.

    Args:
        query: Search query string (required, non-empty)
        ctx: Tool context with db_session and workspace_id
        integration_id: Optional specific GitHub integration ID
        path: Optional path prefix to search within (e.g., "src/")
        extension: Optional file extension filter without dot (e.g., "py", "ts")

    Returns:
        Dictionary with:
        - found (bool): Whether integration was found
        - query (str): Full constructed GitHub search query
        - repository (str): Repository in "owner/repo" format
        - matches (list): List of matching code snippets (empty — not implemented)
        - note (str): Explanation of limitation
        - error (str): Error message if found=False
    """
    if not query or not query.strip():
        return {
            "error": "Search query cannot be empty",
            "found": False,
            "matches": [],
        }

    integration, error = await _get_github_integration(ctx, integration_id)

    if error:
        return {"error": error, "found": False, "matches": []}

    if integration is None:
        return {"error": "Integration not found", "found": False, "matches": []}

    repo_owner, repo_name, repo_error = _extract_repo_info(integration)

    if repo_error:
        return {"error": repo_error, "found": False, "matches": []}

    if repo_owner is None or repo_name is None:
        return {
            "error": "Could not determine repository owner/name from integration settings",
            "found": False,
            "matches": [],
        }

    # Build search query for GitHub
    search_parts = [query.strip(), f"repo:{repo_owner}/{repo_name}"]

    if path:
        # Ensure path doesn't have leading/trailing slashes for consistency
        clean_path = path.strip("/")
        if clean_path:
            search_parts.append(f"path:{clean_path}")

    if extension:
        # Remove leading dot if present
        clean_ext = extension.lstrip(".")
        if clean_ext:
            search_parts.append(f"extension:{clean_ext}")

    full_query = " ".join(search_parts)

    return {
        "found": True,
        "query": full_query,
        "repository": f"{repo_owner}/{repo_name}",
        "matches": [],
        "note": (
            "Code search via GitHub API not yet supported. "
            "Use get_pr_diff to inspect changed files in a PR, "
            "or request specific file content via the note tools."
        ),
    }


@register_tool("github")
async def post_pr_comment(
    pr_number: int,
    body: str,
    ctx: ToolContext,
    integration_id: str | None = None,
    path: str | None = None,
    line: int | None = None,
) -> dict[str, Any]:
    """Post a comment on a pull request.

    AUTO_EXECUTE action (DD-003) with notification to user.
    Can post general comments or line-specific review comments.

    Args:
        pr_number: PR number (must be positive)
        body: Comment body (markdown supported, required non-empty)
        ctx: Tool context with db_session and workspace_id
        integration_id: Optional specific GitHub integration ID
        path: Optional file path for line comment
        line: Optional line number for line comment (requires path)

    Returns:
        Dictionary with:
        - posted (bool): Whether comment was posted
        - comment_id (int): ID of created comment
        - url (str): URL of created comment
        - type (str): "general_comment" or "line_comment"
        - error (str): Error message if posted=False
    """
    input_error: str | None = None
    if pr_number <= 0:
        input_error = f"Invalid PR number: {pr_number} (must be positive)"
    elif not body or not body.strip():
        input_error = "Comment body cannot be empty"
    elif line is not None and not path:
        input_error = "Line comment requires both path and line parameters"

    if input_error:
        return {"error": input_error, "posted": False}

    integration, error = await _get_github_integration(ctx, integration_id)

    if error:
        return {"error": error, "posted": False}

    if integration is None:
        return {"error": "Integration not found", "posted": False}

    repo_owner, repo_name, repo_error = _extract_repo_info(integration)

    if repo_error:
        return {"error": repo_error, "posted": False}

    if repo_owner is None or repo_name is None:
        return {
            "error": "Could not determine repository owner/name from integration settings",
            "posted": False,
        }

    try:
        access_token = decrypt_api_key(integration.access_token)
    except Exception:
        logger.exception("Failed to decrypt GitHub access token for integration %s", integration.id)
        return {"posted": False, "error": "Failed to decrypt access token"}

    comment_type = "line_comment" if path and line else "general_comment"

    async with GitHubClient(access_token) as client:
        try:
            if comment_type == "line_comment" and path is not None and line is not None:
                comment = await client.post_review_comment(
                    repo_owner, repo_name, pr_number, path, line, body
                )
            else:
                comment = await client.post_comment(repo_owner, repo_name, pr_number, body)

            return {
                "posted": True,
                "comment_id": comment["id"],
                "url": comment["html_url"],
                "type": comment_type,
            }
        except GitHubAPIError as e:
            return {"posted": False, "error": str(e)}
