"""RAG helper functions for project MCP tools.

Shared logic for building embedding services and filtering knowledge graph
results to a specific project scope. Used by search_project_knowledge and
get_project_context tools in project_server.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.tools.mcp_server import ToolContext
    from pilot_space.application.services.memory.graph_search_service import (
        GraphSearchResult,
    )
    from pilot_space.infrastructure.database.models.project import Project

logger = get_logger(__name__)


async def build_graph_search(
    db_session: AsyncSession,
    workspace_id: UUID,
) -> tuple[Any, Any]:
    """Build GraphSearchService with workspace BYOK embedding.

    Returns:
        Tuple of (GraphSearchService, EmbeddingService).
    """
    from pilot_space.ai.agents.pilotspace_stream_utils import (
        get_workspace_embedding_key,
    )
    from pilot_space.application.services.embedding_service import (
        EmbeddingConfig,
        EmbeddingService,
    )
    from pilot_space.application.services.memory.graph_search_service import (
        GraphSearchService,
    )
    from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
        KnowledgeGraphRepository,
    )

    openai_key = await get_workspace_embedding_key(db_session, workspace_id)
    embedding_svc = EmbeddingService(EmbeddingConfig(openai_api_key=openai_key))
    kg_repo = KnowledgeGraphRepository(db_session)
    return GraphSearchService(kg_repo, embedding_service=embedding_svc), embedding_svc


def filter_nodes_by_project(
    result: GraphSearchResult,
    project: Project,
) -> list[Any]:
    """Filter scored nodes to only those belonging to the given project.

    Matches on properties.project_id or properties.project_identifier.
    """
    project_id_str = str(project.id)
    filtered = []
    for scored_node in result.nodes:
        props = scored_node.node.properties or {}
        if (
            props.get("project_id") == project_id_str
            or props.get("project_identifier") == project.identifier
        ):
            filtered.append(scored_node)
    return filtered


def format_search_results(scored_nodes: list[Any], max_content: int = 500) -> list[dict[str, Any]]:
    """Format scored nodes into JSON-serializable dicts for tool output."""
    return [
        {
            "node_type": sn.node.node_type,
            "label": sn.node.label,
            "content": (sn.node.content or "")[:max_content],
            "score": round(sn.score, 4),
            "external_id": str(sn.node.external_id) if sn.node.external_id else None,
            "properties": {
                k: v
                for k, v in (sn.node.properties or {}).items()
                if k in ("priority", "state", "identifier", "title")
            },
        }
        for sn in scored_nodes
    ]


def format_knowledge_summary(
    result: GraphSearchResult,
    project_nodes: list[Any],
    max_nodes: int = 10,
    max_content: int = 300,
) -> dict[str, Any]:
    """Format knowledge graph search results as a summary dict."""
    return {
        "total_nodes_found": len(result.nodes),
        "project_relevant": len(project_nodes),
        "embedding_used": result.embedding_used,
        "nodes": [
            {
                "type": sn.node.node_type,
                "label": sn.node.label,
                "content": (sn.node.content or "")[:max_content],
                "score": round(sn.score, 4),
            }
            for sn in project_nodes[:max_nodes]
        ],
    }


async def resolve_project(
    project_id_input: str,
    tool_context: ToolContext,
    *,
    with_states: bool = False,
) -> tuple[Any | None, str | None]:
    """Resolve project by UUID/identifier and validate workspace access.

    Returns:
        Tuple of (project, None) on success, or (None, error_message) on failure.
    """
    from pilot_space.ai.tools.entity_resolver import resolve_entity_id
    from pilot_space.infrastructure.database.repositories.project_repository import (
        ProjectRepository,
    )

    project_uuid, error = await resolve_entity_id("project", project_id_input, tool_context)
    if error or not project_uuid:
        return None, f"Error: {error or 'Invalid project ID'}"

    repo = ProjectRepository(tool_context.db_session)
    project = (
        await repo.get_with_states(project_uuid)
        if with_states
        else await repo.get_by_id(project_uuid)
    )
    if not project or str(project.workspace_id) != tool_context.workspace_id:
        return None, f"Project '{project_id_input}' not found"

    return project, None


__all__ = [
    "build_graph_search",
    "filter_nodes_by_project",
    "format_knowledge_summary",
    "format_search_results",
    "resolve_project",
]
