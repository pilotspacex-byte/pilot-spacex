"""Search MCP tools for Pilot Space.

These tools provide semantic and text-based search across
workspace content including issues, notes, and pages.

T025: semantic_search - Search issues, notes, and content using text matching
T026: search_codebase - Search indexed codebase from GitHub integration
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import or_, select

from pilot_space.ai.tools.mcp_server import ToolContext, register_tool
from pilot_space.infrastructure.database.models import (
    Integration,
    IntegrationProvider,
    Issue,
    Note,
)


@register_tool("search")
async def semantic_search(
    query: str,
    ctx: ToolContext,
    content_types: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Semantic search across workspace content.

    Searches issues, notes, and other content using
    text matching. Will use vector similarity when embeddings
    are available.

    Args:
        query: Search query text
        ctx: Tool context with db_session
        content_types: Filter by type (issue, note) - None means all
        limit: Maximum results (default 10, max 50)

    Returns:
        Search results with relevance scores and excerpts

    Example:
        results = await semantic_search(
            query="authentication bug",
            ctx=ctx,
            content_types=["issue"],
            limit=5
        )
        # Returns: {
        #   "results": [
        #     {
        #       "type": "issue",
        #       "id": "uuid",
        #       "identifier": "PILOT-123",
        #       "title": "Fix auth bug",
        #       "excerpt": "...",
        #       "score": 0.85
        #     }
        #   ],
        #   "total": 1,
        #   "search_method": "text_similarity"
        # }
    """
    limit = min(limit, 50)
    search_pattern = f"%{query.lower()}%"
    results: list[dict[str, Any]] = []

    workspace_uuid = UUID(ctx.workspace_id)

    # Search issues
    if content_types is None or "issue" in content_types:
        issue_query = (
            select(Issue)
            .where(
                Issue.workspace_id == workspace_uuid,
                Issue.is_deleted.is_(False),
                or_(
                    Issue.name.ilike(search_pattern),
                    Issue.description.ilike(search_pattern),
                ),
            )
            .limit(limit)
        )
        issue_result = await ctx.db_session.execute(issue_query)
        issues = issue_result.scalars().all()

        for issue in issues:
            # Calculate simple relevance score based on match location
            score = 0.85  # Default score
            if issue.name and query.lower() in issue.name.lower():
                score = 0.95  # Higher score for title matches

            results.append(
                {
                    "type": "issue",
                    "id": str(issue.id),
                    "identifier": issue.identifier,
                    "title": issue.name,
                    "excerpt": (issue.description or "")[:200],
                    "score": score,
                    "priority": issue.priority.value if issue.priority else "none",
                    "state": issue.state.name if issue.state else None,
                }
            )

    # Search notes
    if content_types is None or "note" in content_types:
        note_query = (
            select(Note)
            .where(
                Note.workspace_id == workspace_uuid,
                Note.is_deleted.is_(False),
                or_(
                    Note.title.ilike(search_pattern),
                    # Note: content is JSONB, would need custom search for body text
                ),
            )
            .limit(limit)
        )
        note_result = await ctx.db_session.execute(note_query)
        notes = note_result.scalars().all()

        for note in notes:
            # Calculate simple relevance score
            score = 0.80  # Default score for notes
            if note.title and query.lower() in note.title.lower():
                score = 0.90

            results.append(
                {
                    "type": "note",
                    "id": str(note.id),
                    "title": note.title,
                    "excerpt": (note.summary or "")[:200],
                    "score": score,
                    "word_count": note.word_count,
                    "is_pinned": note.is_pinned,
                }
            )

    # Sort by score descending and limit
    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "results": results[:limit],
        "total": len(results),
        "search_method": "text_similarity",  # Will be "vector" when pgvector ready
        "query": query,
    }


@register_tool("search")
async def search_codebase(
    query: str,
    ctx: ToolContext,
    repo_id: str | None = None,
    file_pattern: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search indexed codebase for patterns.

    Searches code indexed from GitHub integration.
    Returns matching files and snippets.

    Args:
        query: Search query (regex supported in future)
        ctx: Tool context with db_session
        repo_id: Optional repository integration ID
        file_pattern: Glob pattern for files (e.g., "*.py")
        limit: Maximum results (default 10, max 50)

    Returns:
        Matching code snippets with file paths

    Example:
        results = await search_codebase(
            query="async def create_issue",
            ctx=ctx,
            file_pattern="*.py",
            limit=10
        )
        # Returns: {
        #   "found": True,
        #   "matches": [],
        #   "note": "Code search requires GitHub code indexing",
        #   "integrations": [...]
        # }
    """
    limit = min(limit, 50)
    workspace_uuid = UUID(ctx.workspace_id)

    # Check if GitHub integration exists
    integration_query = select(Integration).where(
        Integration.workspace_id == workspace_uuid,
        Integration.provider == IntegrationProvider.GITHUB,
        Integration.is_deleted.is_(False),
    )

    if repo_id:
        integration_query = integration_query.where(Integration.id == UUID(repo_id))

    result = await ctx.db_session.execute(integration_query)
    integrations = result.scalars().all()

    if not integrations:
        return {
            "error": "No GitHub integration found for this workspace",
            "found": False,
            "matches": [],
            "query": query,
        }

    # Note: Actual code search would use indexed content
    # For MVP, return placeholder indicating feature availability
    integration_info = []
    for integration in integrations:
        # Safe access to metadata (might be None)
        metadata = integration.settings or {}
        integration_info.append(
            {
                "id": str(integration.id),
                "repo_name": metadata.get("repo_name"),
                "external_account": integration.external_account_name,
            }
        )

    return {
        "found": True,
        "matches": [],
        "note": "Code search requires GitHub code indexing (pending implementation)",
        "integrations": integration_info,
        "query": query,
        "file_pattern": file_pattern,
        "limit": limit,
    }
