"""Search MCP tools for Pilot Space.

These tools provide semantic and text-based search across
workspace content including issues, notes, and pages.

T025: semantic_search - Hybrid search via GraphSearchService (pgvector + text),
      with ILIKE fallback when GraphSearchService is unavailable.
T026: search_codebase - Reports not_implemented status (code indexing not available).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import or_, select

from pilot_space.ai.tools.mcp_server import ToolContext, register_tool
from pilot_space.application.services.memory.graph_search_service import (
    GraphSearchPayload,
    GraphSearchResult,
    GraphSearchService,
)
from pilot_space.domain.graph_node import NodeType
from pilot_space.infrastructure.database.models import (
    Issue,
    Note,
)

# Map content_type strings to NodeType enums for GraphSearchService
_CONTENT_TYPE_TO_NODE_TYPES: dict[str, list[NodeType]] = {
    "issue": [NodeType.ISSUE],
    "note": [NodeType.NOTE, NodeType.NOTE_CHUNK],
}


def _map_content_types(content_types: list[str] | None) -> list[NodeType] | None:
    """Map content_type strings to NodeType enums.

    Args:
        content_types: List of content type strings (e.g., ["issue", "note"]).

    Returns:
        None if no filter requested (content_types is None — means "all types").
        Empty list if content_types was provided but none mapped (means "no matches").
        Non-empty list of NodeType enums for valid mappings.
    """
    if content_types is None:
        return None
    node_types: list[NodeType] = []
    for ct in content_types:
        mapped = _CONTENT_TYPE_TO_NODE_TYPES.get(ct)
        if mapped:
            node_types.extend(mapped)
    # Return empty list (not None) when all entries are unmapped —
    # this signals "no valid types" rather than "search everything".
    return node_types


def _format_graph_results(result: GraphSearchResult) -> dict[str, Any]:
    """Format GraphSearchResult into the MCP tool response dict.

    Args:
        result: GraphSearchResult from GraphSearchService.execute().

    Returns:
        Dict with results list, total, search_method, and query.
    """
    results: list[dict[str, Any]] = []
    for scored in result.nodes:
        node = scored.node
        results.append(
            {
                "type": node.node_type.value,
                "id": str(node.id),
                "title": node.label,
                "excerpt": (node.content or "")[:200],
                "score": scored.score,
            }
        )
    return {
        "results": results,
        "total": len(results),
        "search_method": "hybrid" if result.embedding_used else "text_similarity",
        "query": result.query,
    }


@register_tool("search")
async def semantic_search(
    query: str,
    ctx: ToolContext,
    content_types: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Semantic search across workspace content.

    Uses GraphSearchService for hybrid search (pgvector cosine + full-text)
    when available. Falls back to ILIKE text matching otherwise.

    Args:
        query: Search query text
        ctx: Tool context with db_session
        content_types: Filter by type (issue, note) - None means all
        limit: Maximum results (default 10, max 50)

    Returns:
        Search results with relevance scores and excerpts
    """
    limit = min(limit, 50)
    workspace_uuid = UUID(ctx.workspace_id)

    # Hybrid path: delegate to GraphSearchService when available
    graph_search_service: GraphSearchService | None = ctx.extra.get("graph_search_service")
    if graph_search_service is not None:
        payload = GraphSearchPayload(
            query=query,
            workspace_id=workspace_uuid,
            user_id=UUID(ctx.user_id) if ctx.user_id else None,
            node_types=_map_content_types(content_types),
            limit=limit,
        )
        result = await graph_search_service.execute(payload)
        return _format_graph_results(result)

    # Fallback: ILIKE text search (backward compatibility)
    return await _text_fallback_search(query, ctx, content_types, limit, workspace_uuid)


async def _text_fallback_search(
    query: str,
    ctx: ToolContext,
    content_types: list[str] | None,
    limit: int,
    workspace_uuid: UUID,
) -> dict[str, Any]:
    """ILIKE text search fallback when GraphSearchService is unavailable.

    Args:
        query: Search query text.
        ctx: Tool context with db_session.
        content_types: Filter by type (issue, note).
        limit: Maximum results.
        workspace_uuid: Pre-parsed workspace UUID.

    Returns:
        Search results dict with text_similarity method.
    """
    search_pattern = f"%{query.lower()}%"
    results: list[dict[str, Any]] = []

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
            score = 0.85
            if issue.name and query.lower() in issue.name.lower():
                score = 0.95

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
            score = 0.80
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

    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "results": results[:limit],
        "total": len(results),
        "search_method": "text_similarity",
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
    """Check codebase search availability.

    Code indexing from GitHub integration is not yet implemented.
    Returns an explicit not_implemented status without querying the database.

    Args:
        query: Search query
        ctx: Tool context with db_session
        repo_id: Optional repository integration ID
        file_pattern: Glob pattern for files (e.g., "*.py")
        limit: Maximum results (default 10, max 50)

    Returns:
        Status dict with found=False and not_implemented status
    """
    return {
        "found": False,
        "status": "not_implemented",
        "message": "Code search is not yet available. Code indexing has not been implemented.",
        "query": query,
        "file_pattern": file_pattern,
    }
