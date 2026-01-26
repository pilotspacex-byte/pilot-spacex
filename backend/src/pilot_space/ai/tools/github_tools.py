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

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.integration import Integration


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
    author, reviewers, and CI status.

    This tool currently returns a placeholder response indicating
    the integration connection status. Full GitHub API integration
    is pending - use gh CLI or direct API calls for actual PR data.

    Args:
        pr_number: PR number in the repository (must be positive)
        ctx: Tool context with db_session and workspace_id
        integration_id: Optional specific GitHub integration ID

    Returns:
        Dictionary with:
        - found (bool): Whether integration was found
        - pr (dict): PR metadata (placeholder in MVP)
        - error (str): Error message if found=False
        - note (str): Implementation status note

    Example:
        >>> await get_pr_details(
        ...     pr_number=123, ctx=ToolContext(db_session=session, workspace_id=ws_id)
        ... )
        {
            "found": True,
            "pr": {
                "number": 123,
                "repository": "octocat/hello-world",
                "integration_id": "uuid-here"
            },
            "note": "GitHub API integration pending..."
        }
    """
    if pr_number <= 0:
        return {
            "error": f"Invalid PR number: {pr_number} (must be positive)",
            "found": False,
        }

    integration, error = await _get_github_integration(ctx, integration_id)

    if error:
        return {"error": error, "found": False}

    assert integration is not None  # Type narrowing after error check

    repo_owner, repo_name, repo_error = _extract_repo_info(integration)

    if repo_error:
        return {"error": repo_error, "found": False}

    assert repo_owner is not None
    assert repo_name is not None

    # Note: Actual GitHub API call would go here
    # Example implementation:
    # from github import Github
    # gh = Github(integration.access_token)
    # repo = gh.get_repo(f"{repo_owner}/{repo_name}")
    # pr = repo.get_pull(pr_number)
    # return {
    #     "found": True,
    #     "pr": {
    #         "number": pr.number,
    #         "title": pr.title,
    #         "body": pr.body,
    #         "state": pr.state,
    #         "author": pr.user.login,
    #         "created_at": pr.created_at.isoformat(),
    #         "updated_at": pr.updated_at.isoformat(),
    #         "mergeable": pr.mergeable,
    #         "merged": pr.merged,
    #         "draft": pr.draft,
    #     }
    # }

    # For MVP, return placeholder showing integration is connected
    return {
        "found": True,
        "pr": {
            "number": pr_number,
            "repository": f"{repo_owner}/{repo_name}",
            "integration_id": str(integration.id),
            "settings_available": bool(integration.settings),
        },
        "note": "GitHub API integration pending - use gh CLI or direct API for PR details",
    }


@register_tool("github")
async def get_pr_diff(
    pr_number: int,
    ctx: ToolContext,
    integration_id: str | None = None,
) -> dict[str, Any]:
    """Get full unified diff for a pull request.

    Retrieves the complete diff for code review analysis.
    Returns file-by-file changes with additions/deletions.

    This tool currently returns a placeholder response indicating
    the integration connection status. Full GitHub API integration
    is pending - use gh CLI or direct API calls for actual diffs.

    Args:
        pr_number: PR number in the repository (must be positive)
        ctx: Tool context with db_session and workspace_id
        integration_id: Optional specific GitHub integration ID

    Returns:
        Dictionary with:
        - found (bool): Whether integration was found
        - pr_number (int): The requested PR number
        - repository (str): Repository in "owner/repo" format
        - diff (str | None): Unified diff content (None in MVP)
        - files (list): List of changed files (empty in MVP)
        - stats (dict): Change statistics (zeros in MVP)
        - error (str): Error message if found=False
        - note (str): Implementation status note

    Example:
        >>> await get_pr_diff(
        ...     pr_number=123, ctx=ToolContext(db_session=session, workspace_id=ws_id)
        ... )
        {
            "found": True,
            "pr_number": 123,
            "repository": "octocat/hello-world",
            "diff": None,
            "files": [],
            "stats": {"additions": 0, "deletions": 0, "changed_files": 0},
            "note": "GitHub API integration pending..."
        }
    """
    if pr_number <= 0:
        return {
            "error": f"Invalid PR number: {pr_number} (must be positive)",
            "found": False,
        }

    integration, error = await _get_github_integration(ctx, integration_id)

    if error:
        return {"error": error, "found": False}

    assert integration is not None

    repo_owner, repo_name, repo_error = _extract_repo_info(integration)

    if repo_error:
        return {"error": repo_error, "found": False}

    assert repo_owner is not None
    assert repo_name is not None

    # Note: Actual GitHub API call for diff would go here
    # Example implementation:
    # from github import Github
    # gh = Github(integration.access_token)
    # repo = gh.get_repo(f"{repo_owner}/{repo_name}")
    # pr = repo.get_pull(pr_number)
    #
    # files = []
    # total_additions = 0
    # total_deletions = 0
    #
    # for file in pr.get_files():
    #     files.append({
    #         "filename": file.filename,
    #         "status": file.status,
    #         "additions": file.additions,
    #         "deletions": file.deletions,
    #         "changes": file.changes,
    #         "patch": file.patch,
    #     })
    #     total_additions += file.additions
    #     total_deletions += file.deletions
    #
    # return {
    #     "found": True,
    #     "pr_number": pr_number,
    #     "repository": f"{repo_owner}/{repo_name}",
    #     "diff": "\n".join(f["patch"] for f in files if f.get("patch")),
    #     "files": files,
    #     "stats": {
    #         "additions": total_additions,
    #         "deletions": total_deletions,
    #         "changed_files": len(files),
    #     },
    # }

    # For MVP, return placeholder
    return {
        "found": True,
        "pr_number": pr_number,
        "repository": f"{repo_owner}/{repo_name}",
        "diff": None,
        "files": [],
        "stats": {
            "additions": 0,
            "deletions": 0,
            "changed_files": 0,
        },
        "note": "GitHub API integration pending - use gh CLI for diffs (e.g., gh pr diff 123)",
    }


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

    This tool currently returns a placeholder response indicating
    the integration connection status. Full GitHub API integration
    is pending - use gh CLI or GitHub web interface for actual searches.

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
        - matches (list): List of matching code snippets (empty in MVP)
        - error (str): Error message if found=False
        - note (str): Implementation status note

    Example:
        >>> await search_code_in_repo(
        ...     query="async def",
        ...     ctx=ToolContext(db_session=session, workspace_id=ws_id),
        ...     extension="py",
        ... )
        {
            "found": True,
            "query": "async def repo:octocat/hello-world extension:py",
            "repository": "octocat/hello-world",
            "matches": [],
            "note": "GitHub code search API integration pending"
        }
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

    assert integration is not None

    repo_owner, repo_name, repo_error = _extract_repo_info(integration)

    if repo_error:
        return {"error": repo_error, "found": False, "matches": []}

    assert repo_owner is not None
    assert repo_name is not None

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

    # Note: Actual GitHub code search API call would go here
    # Example implementation:
    # from github import Github
    # gh = Github(integration.access_token)
    # results = gh.search_code(full_query)
    #
    # matches = []
    # for item in results[:50]:  # Limit to first 50 results
    #     matches.append({
    #         "path": item.path,
    #         "repository": item.repository.full_name,
    #         "sha": item.sha,
    #         "url": item.html_url,
    #         "score": item.score,
    #         # Note: GitHub API doesn't return content in search results
    #         # Would need separate API call to get file content
    #     })
    #
    # return {
    #     "found": True,
    #     "query": full_query,
    #     "repository": f"{repo_owner}/{repo_name}",
    #     "matches": matches,
    #     "total_count": results.totalCount,
    # }

    # For MVP, return placeholder
    return {
        "found": True,
        "query": full_query,
        "repository": f"{repo_owner}/{repo_name}",
        "matches": [],
        "note": "GitHub code search API integration pending - use gh CLI (e.g., gh search code 'query')",
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
        - pr_number (int): PR number
        - repository (str): Repository in "owner/repo" format
        - comment_type (str): "general_comment" or "line_comment"
        - body_preview (str): Preview of comment body
        - path (str | None): File path if line comment
        - line (int | None): Line number if line comment
        - error (str): Error message if posted=False
        - note (str): Implementation status note
    """
    if pr_number <= 0:
        return {
            "error": f"Invalid PR number: {pr_number} (must be positive)",
            "posted": False,
        }

    if not body or not body.strip():
        return {
            "error": "Comment body cannot be empty",
            "posted": False,
        }

    if line is not None and not path:
        return {
            "error": "Line comment requires both path and line parameters",
            "posted": False,
        }

    integration, error = await _get_github_integration(ctx, integration_id)

    if error:
        return {"error": error, "posted": False}

    assert integration is not None

    repo_owner, repo_name, repo_error = _extract_repo_info(integration)

    if repo_error:
        return {"error": repo_error, "posted": False}

    assert repo_owner is not None
    assert repo_name is not None

    comment_type = "line_comment" if path and line else "general_comment"

    # Note: Actual GitHub API call would post the comment
    # Example implementation:
    # from github import Github
    # gh = Github(integration.access_token)
    # repo = gh.get_repo(f"{repo_owner}/{repo_name}")
    # pr = repo.get_pull(pr_number)
    #
    # if comment_type == "line_comment":
    #     # Post review comment on specific line
    #     commit = pr.get_commits()[pr.commits - 1]  # Latest commit
    #     pr.create_review_comment(
    #         body=body,
    #         commit=commit,
    #         path=path,
    #         line=line,
    #     )
    # else:
    #     # Post general PR comment
    #     pr.create_issue_comment(body)
    #
    # return {
    #     "posted": True,
    #     "pr_number": pr_number,
    #     "repository": f"{repo_owner}/{repo_name}",
    #     "comment_type": comment_type,
    #     "body_preview": body[:200],
    #     "path": path,
    #     "line": line,
    #     "comment_id": comment.id,
    #     "url": comment.html_url,
    # }

    # For MVP, return placeholder
    return {
        "posted": False,  # Would be True after actual API call
        "pr_number": pr_number,
        "repository": f"{repo_owner}/{repo_name}",
        "comment_type": comment_type,
        "body_preview": body[:200] if len(body) > 200 else body,
        "path": path,
        "line": line,
        "note": "GitHub API integration pending - comment not actually posted. Use gh CLI (e.g., gh pr comment 123 --body 'text')",
    }
