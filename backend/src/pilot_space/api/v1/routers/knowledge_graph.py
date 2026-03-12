"""Knowledge Graph REST API router.

Provides hybrid search, neighbor traversal, subgraph extraction, user
context, and issue-scoped graph endpoints for the knowledge graph feature.

Endpoints:
  GET  /api/v1/workspaces/{workspace_id}/knowledge-graph/search
  GET  /api/v1/workspaces/{workspace_id}/knowledge-graph/nodes/{node_id}/neighbors
  GET  /api/v1/workspaces/{workspace_id}/knowledge-graph/subgraph
  GET  /api/v1/workspaces/{workspace_id}/knowledge-graph/user-context
  GET  /api/v1/workspaces/{workspace_id}/issues/{issue_id}/knowledge-graph

Feature 016: Knowledge Graph — Unit 7 REST API
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, TypeVar
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import select

from pilot_space.ai.agents.pilotspace_stream_utils import get_workspace_openai_key
from pilot_space.api.v1.schemas.knowledge_graph import (
    GraphEdgeDTO,
    GraphNodeDTO,
    GraphResponse,
)
from pilot_space.application.services.embedding_service import EmbeddingConfig, EmbeddingService
from pilot_space.application.services.memory.graph_search_service import (
    GraphSearchPayload,
    GraphSearchService,
)
from pilot_space.dependencies.auth import SessionDep, SyncedUserId
from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.database.models.integration import (
    IntegrationLink,
    IntegrationLinkType,
)
from pilot_space.infrastructure.database.models.issue import Issue as IssueModel
from pilot_space.infrastructure.database.models.project import Project as ProjectModel
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

_EnumT = TypeVar("_EnumT", bound=StrEnum)


def _parse_csv_enum(
    raw: str | None,
    enum_cls: type[_EnumT],
    param_name: str,
) -> list[_EnumT] | None:
    """Parse a comma-separated enum string into a list of enum values.

    Raises HTTP 422 with a descriptive message on invalid values.
    """
    if not raw:
        return None
    try:
        return [enum_cls(t.strip()) for t in raw.split(",") if t.strip()]  # type: ignore[call-arg]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {param_name}: {exc}") from exc


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/workspaces/{workspace_id}/knowledge-graph",
    tags=["knowledge-graph"],
)

# Separate router for the issue-scoped endpoint — different path prefix
issues_kg_router = APIRouter(
    prefix="/workspaces/{workspace_id}",
    tags=["knowledge-graph"],
)

# Separate router for the project-scoped endpoint — different path prefix
projects_kg_router = APIRouter(
    prefix="/workspaces/{workspace_id}",
    tags=["knowledge-graph"],
)

WorkspaceIdPath = Annotated[UUID, Path(description="Workspace UUID")]

# ---------------------------------------------------------------------------
# Node importance tiers for sorting
# ---------------------------------------------------------------------------

_TIER_HIGH: frozenset[str] = frozenset(
    {
        NodeType.ISSUE.value,
        NodeType.NOTE.value,
        NodeType.DECISION.value,
        NodeType.PROJECT.value,
    }
)
_TIER_MID: frozenset[str] = frozenset(
    {
        NodeType.PULL_REQUEST.value,
        NodeType.BRANCH.value,
        NodeType.COMMIT.value,
        NodeType.CODE_REFERENCE.value,
        NodeType.WORK_INTENT.value,
    }
)
# All others fall to tier 3 (summary, skill_outcome, etc.)


def _node_tier(node_type: str) -> int:
    """Return sort priority tier (lower = higher priority)."""
    if node_type in _TIER_HIGH:
        return 0
    if node_type in _TIER_MID:
        return 1
    return 2


# ---------------------------------------------------------------------------
# Domain → DTO mappers
# ---------------------------------------------------------------------------

_EDGE_LABELS: dict[EdgeType, str] = {
    EdgeType.RELATES_TO: "related to",
    EdgeType.CAUSED_BY: "caused by",
    EdgeType.LED_TO: "led to",
    EdgeType.DECIDED_IN: "decided in",
    EdgeType.AUTHORED_BY: "authored by",
    EdgeType.ASSIGNED_TO: "assigned to",
    EdgeType.BELONGS_TO: "belongs to",
    EdgeType.REFERENCES: "references",
    EdgeType.LEARNED_FROM: "learned from",
    EdgeType.SUMMARIZES: "summarizes",
    EdgeType.BLOCKS: "blocks",
    EdgeType.DUPLICATES: "duplicates",
    EdgeType.PARENT_OF: "parent of",
}


def _node_to_dto(node: GraphNode, score: float | None = None) -> GraphNodeDTO:
    """Map a domain GraphNode to a GraphNodeDTO.

    Args:
        node: Domain graph node entity.
        score: Optional relevance score from search.

    Returns:
        GraphNodeDTO ready for JSON serialization.
    """
    return GraphNodeDTO(
        id=str(node.id),
        node_type=node.node_type.value,
        label=node.label,
        summary=node.summary or None,
        properties=node.properties,  # type: ignore[arg-type]
        created_at=node.created_at,
        updated_at=node.updated_at,
        score=score,
    )


def _edge_to_dto(edge: GraphEdge) -> GraphEdgeDTO:
    """Map a domain GraphEdge to a GraphEdgeDTO."""
    edge_type_str = edge.edge_type.value
    label = _EDGE_LABELS.get(edge.edge_type, edge_type_str)
    return GraphEdgeDTO(
        id=str(edge.id),
        source_id=str(edge.source_id),
        target_id=str(edge.target_id),
        edge_type=edge_type_str,
        label=label,
        weight=edge.weight,
        properties=edge.properties,  # type: ignore[arg-type]
    )


def _edges_to_dtos(edges: list[GraphEdge]) -> list[GraphEdgeDTO]:
    """Batch-convert domain edges to DTOs."""
    return [_edge_to_dto(e) for e in edges]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/search",
    response_model=GraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Hybrid knowledge graph search",
    description=(
        "Search workspace knowledge graph using hybrid vector + full-text + "
        "recency scoring. Falls back to keyword-only on SQLite / when no "
        "embedding is available."
    ),
)
async def search_knowledge_graph(
    workspace_id: WorkspaceIdPath,
    session: SessionDep,
    current_user_id: SyncedUserId,
    q: Annotated[str, Query(min_length=1, max_length=2000, description="Query text")],
    node_types: Annotated[
        str | None,
        Query(description="Comma-separated NodeType values to filter by"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="Maximum results")] = 10,
) -> GraphResponse:
    """Search knowledge graph nodes with hybrid scoring."""
    await set_rls_context(session, current_user_id, workspace_id)

    parsed_types: list[NodeType] | None = _parse_csv_enum(node_types, NodeType, "node_type")

    # Look up workspace OpenAI key for vector embedding (BYOK pattern)
    openai_api_key = await get_workspace_openai_key(session, workspace_id)
    embedding_svc = EmbeddingService(EmbeddingConfig(openai_api_key=openai_api_key))

    repo = KnowledgeGraphRepository(session)
    service = GraphSearchService(repo, embedding_service=embedding_svc)
    result = await service.execute(
        GraphSearchPayload(
            query=q,
            workspace_id=workspace_id,
            user_id=current_user_id,
            node_types=parsed_types,
            limit=limit,
        )
    )

    node_dtos = [_node_to_dto(sn.node, score=sn.score) for sn in result.nodes]
    return GraphResponse(nodes=node_dtos, edges=_edges_to_dtos(result.edges))


@router.get(
    "/nodes/{node_id}/neighbors",
    response_model=GraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Get neighboring nodes",
    description="Return nodes reachable from node_id within the given traversal depth.",
)
async def get_node_neighbors(
    workspace_id: WorkspaceIdPath,
    node_id: Annotated[UUID, Path(description="Source node UUID")],
    session: SessionDep,
    current_user_id: SyncedUserId,
    depth: Annotated[int, Query(ge=1, le=4, description="Traversal depth")] = 1,
    edge_types: Annotated[
        str | None,
        Query(description="Comma-separated EdgeType values to restrict traversal"),
    ] = None,
) -> GraphResponse:
    """Return local neighborhood subgraph around the given node."""
    await set_rls_context(session, current_user_id, workspace_id)

    parsed_edge_types: list[EdgeType] | None = _parse_csv_enum(edge_types, EdgeType, "edge_type")

    repo = KnowledgeGraphRepository(session)
    neighbors = await repo.get_neighbors(
        node_id=node_id,
        edge_types=parsed_edge_types,
        depth=depth,
        workspace_id=workspace_id,
    )

    # Fetch center node so it is included in `nodes` alongside neighbors.
    # Without this, edges referencing center_node_id would be dangling references
    # in any graph renderer that relies solely on the `nodes` array.
    center_node = await repo.get_node_by_id(node_id, workspace_id)
    all_nodes = ([center_node] if center_node else []) + neighbors
    all_ids = [n.id for n in all_nodes]
    edges = await repo.get_edges_between(all_ids, workspace_id=workspace_id)
    node_dtos = [_node_to_dto(n) for n in all_nodes]
    return GraphResponse(nodes=node_dtos, edges=_edges_to_dtos(edges), center_node_id=node_id)


@router.get(
    "/subgraph",
    response_model=GraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract visual subgraph",
    description="Extract a depth-bounded subgraph rooted at root_id for graph visualization.",
)
async def get_subgraph(
    workspace_id: WorkspaceIdPath,
    session: SessionDep,
    current_user_id: SyncedUserId,
    root_id: Annotated[UUID, Query(description="Root node UUID")],
    max_depth: Annotated[int, Query(ge=1, le=4, description="Maximum traversal depth")] = 2,
    max_nodes: Annotated[int, Query(ge=5, le=100, description="Maximum node count")] = 50,
) -> GraphResponse:
    """Extract a subgraph for visualization centered on root_id."""
    await set_rls_context(session, current_user_id, workspace_id)

    repo = KnowledgeGraphRepository(session)
    if not await repo.get_node_by_id(root_id, workspace_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Root node not found")
    nodes, edges = await repo.get_subgraph(
        root_id=root_id,
        max_depth=max_depth,
        max_nodes=max_nodes,
        workspace_id=workspace_id,
    )

    node_dtos = [_node_to_dto(n) for n in nodes]
    return GraphResponse(nodes=node_dtos, edges=_edges_to_dtos(edges), center_node_id=root_id)


@router.get(
    "/user-context",
    response_model=GraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Personal context nodes",
    description=(
        "Return nodes scoped to the current user plus recent workspace activity. "
        "Useful for populating AI context with personal history."
    ),
)
async def get_user_context(
    workspace_id: WorkspaceIdPath,
    session: SessionDep,
    current_user_id: SyncedUserId,
    limit: Annotated[int, Query(ge=1, le=50, description="Maximum nodes")] = 10,
) -> GraphResponse:
    """Return personal context nodes for the current user."""
    await set_rls_context(session, current_user_id, workspace_id)

    repo = KnowledgeGraphRepository(session)
    nodes = await repo.get_user_context(
        user_id=current_user_id,
        workspace_id=workspace_id,
        limit=limit,
    )

    node_dtos = [_node_to_dto(n) for n in nodes]
    return GraphResponse(nodes=node_dtos, edges=[])


# ---------------------------------------------------------------------------
# Issue-scoped endpoint
# ---------------------------------------------------------------------------

_GITHUB_NODE_TYPE_MAP: dict[IntegrationLinkType, str] = {
    IntegrationLinkType.PULL_REQUEST: NodeType.PULL_REQUEST.value,
    IntegrationLinkType.BRANCH: NodeType.BRANCH.value,
    IntegrationLinkType.COMMIT: NodeType.COMMIT.value,
    IntegrationLinkType.MENTION: NodeType.NOTE.value,
}


@issues_kg_router.get(
    "/issues/{issue_id}/knowledge-graph",
    response_model=GraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue-scoped knowledge graph",
    description=(
        "Return the knowledge graph subgraph connected to a specific issue. "
        "When include_github=true, ephemeral PR/branch/commit nodes are "
        "synthesized from integration_links and appended (not persisted)."
    ),
)
async def get_issue_knowledge_graph(
    workspace_id: WorkspaceIdPath,
    issue_id: Annotated[UUID, Path(description="Issue UUID")],
    session: SessionDep,
    current_user_id: SyncedUserId,
    depth: Annotated[int, Query(ge=1, le=4, description="Traversal depth")] = 2,
    node_types: Annotated[
        str | None,
        Query(description="Comma-separated NodeType filter"),
    ] = None,
    max_nodes: Annotated[int, Query(ge=5, le=100, description="Maximum nodes")] = 50,
    include_github: Annotated[
        bool,
        Query(description="Append ephemeral GitHub nodes from integration_links"),
    ] = True,
) -> GraphResponse:
    """Return knowledge graph subgraph for an issue, optionally enriched with GitHub links."""
    await set_rls_context(session, current_user_id, workspace_id)

    # H-4: Verify the issue exists in this workspace before querying the graph.
    issue_exists = (
        await session.execute(
            select(IssueModel.id).where(
                IssueModel.id == issue_id,
                IssueModel.workspace_id == workspace_id,
                IssueModel.is_deleted == False,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if issue_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    # Step 1: Find the graph node linked to this issue
    stmt = (
        select(GraphNodeModel)
        .where(
            GraphNodeModel.external_id == issue_id,
            GraphNodeModel.workspace_id == workspace_id,
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    graph_node_model = result.scalar_one_or_none()

    # Step 2: No graph node found — return empty response
    if graph_node_model is None:
        logger.info(
            "knowledge_graph_issue_no_node",
            issue_id=str(issue_id),
            workspace_id=str(workspace_id),
        )
        return GraphResponse(nodes=[], edges=[], center_node_id=issue_id)

    center_node_id = graph_node_model.id

    # Step 3: Extract subgraph from the graph node.
    # When node_types filter is active, fetch the maximum pool (100) before filtering
    # to avoid silently dropping valid nodes that were pruned by max_nodes before the
    # filter was applied (devil's advocate W-2).
    repo = KnowledgeGraphRepository(session)
    _fetch_max = 100 if node_types else max_nodes
    nodes, edges = await repo.get_subgraph(
        root_id=center_node_id,
        max_depth=depth,
        max_nodes=_fetch_max,
        workspace_id=workspace_id,
    )

    # Apply node type filter, then trim to requested max_nodes
    if node_types:
        allowed = {t.strip() for t in node_types.split(",") if t.strip()}
        nodes = [n for n in nodes if n.node_type.value in allowed][:max_nodes]

    node_dtos = [_node_to_dto(n) for n in nodes]
    edge_dtos = _edges_to_dtos(edges)

    # Step 4: Synthesize ephemeral GitHub nodes if requested
    if include_github:
        gh_stmt = select(IntegrationLink).where(
            IntegrationLink.issue_id == issue_id,
            IntegrationLink.workspace_id == workspace_id,
            IntegrationLink.is_deleted == False,  # noqa: E712
        )
        gh_result = await session.execute(gh_stmt)
        integration_links = gh_result.scalars().all()

        existing_external_ids = {
            str(n.properties["external_id"])
            for n in node_dtos
            if n.properties and n.properties.get("external_id") is not None
        }
        now = datetime.now(tz=UTC)

        for link in integration_links:
            # Avoid duplicates if a real graph node already represents this link
            if str(link.external_id) in existing_external_ids:
                continue

            mapped_type = _GITHUB_NODE_TYPE_MAP.get(link.link_type, NodeType.NOTE.value)
            node_dtos.append(
                GraphNodeDTO(
                    # Deterministic ID from external_id so repeated fetches
                    # produce stable node IDs for frontend graph reconciliation.
                    id=str(uuid5(NAMESPACE_URL, f"ephemeral:{link.external_id}")),
                    node_type=mapped_type,
                    label=link.title or link.external_id,
                    summary=f"GitHub {link.link_type.value}: {link.title or link.external_id}",
                    properties={
                        "external_id": link.external_id,
                        "external_url": link.external_url,
                        "author_name": link.author_name,
                        "ephemeral": True,
                    },
                    created_at=now,
                    updated_at=now,
                    score=None,
                )
            )

    # Step 5: Sort by importance tier
    node_dtos.sort(key=lambda n: _node_tier(n.node_type))

    return GraphResponse(
        nodes=node_dtos,
        edges=edge_dtos,
        center_node_id=center_node_id,
    )


# ---------------------------------------------------------------------------
# Project-scoped endpoint
# ---------------------------------------------------------------------------


@projects_kg_router.get(
    "/projects/{project_id}/knowledge-graph",
    response_model=GraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Project-scoped knowledge graph",
    description=(
        "Return the knowledge graph subgraph connected to a specific project. "
        "When include_github=true, ephemeral PR/branch/commit nodes are "
        "synthesized from integration_links of project issues and appended (not persisted)."
    ),
)
async def get_project_knowledge_graph(
    workspace_id: WorkspaceIdPath,
    project_id: Annotated[UUID, Path(description="Project UUID")],
    session: SessionDep,
    current_user_id: SyncedUserId,
    depth: Annotated[int, Query(ge=1, le=4, description="Traversal depth")] = 2,
    node_types: Annotated[
        str | None,
        Query(description="Comma-separated NodeType filter"),
    ] = None,
    max_nodes: Annotated[int, Query(ge=5, le=200, description="Maximum nodes")] = 50,
    include_github: Annotated[
        bool,
        Query(description="Append ephemeral GitHub nodes from integration_links"),
    ] = True,
) -> GraphResponse:
    """Return knowledge graph subgraph for a project, optionally enriched with GitHub links."""
    await set_rls_context(session, current_user_id, workspace_id)

    # Verify the project exists in this workspace before querying the graph.
    project_exists = (
        await session.execute(
            select(ProjectModel.id).where(
                ProjectModel.id == project_id,
                ProjectModel.workspace_id == workspace_id,
                ProjectModel.is_deleted == False,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if project_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Step 1: Find the graph node linked to this project
    stmt = (
        select(GraphNodeModel)
        .where(
            GraphNodeModel.external_id == project_id,
            GraphNodeModel.workspace_id == workspace_id,
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    graph_node_model = result.scalar_one_or_none()

    # Step 2: No graph node found — return empty response
    if graph_node_model is None:
        logger.info(
            "knowledge_graph_project_no_node",
            project_id=str(project_id),
            workspace_id=str(workspace_id),
        )
        return GraphResponse(nodes=[], edges=[], center_node_id=project_id)

    center_node_id = graph_node_model.id

    # Step 3: Extract subgraph from the graph node.
    # When node_types filter is active, fetch the maximum pool before filtering
    # to avoid silently dropping valid nodes that were pruned by max_nodes before
    # the filter was applied.
    repo = KnowledgeGraphRepository(session)
    _fetch_max = 200 if node_types else max_nodes
    nodes, edges = await repo.get_subgraph(
        root_id=center_node_id,
        max_depth=depth,
        max_nodes=_fetch_max,
        workspace_id=workspace_id,
    )

    # Apply node type filter, then trim to requested max_nodes
    if node_types:
        allowed = {t.strip() for t in node_types.split(",") if t.strip()}
        nodes = [n for n in nodes if n.node_type.value in allowed][:max_nodes]

    node_dtos = [_node_to_dto(n) for n in nodes]
    edge_dtos = _edges_to_dtos(edges)

    # Step 4: Synthesize ephemeral GitHub nodes if requested
    if include_github:
        gh_stmt = select(IntegrationLink).where(
            IntegrationLink.issue_id.in_(
                select(IssueModel.id).where(
                    IssueModel.project_id == project_id,
                    IssueModel.workspace_id == workspace_id,
                    IssueModel.is_deleted == False,  # noqa: E712
                )
            ),
            IntegrationLink.workspace_id == workspace_id,
            IntegrationLink.is_deleted == False,  # noqa: E712
        )
        gh_result = await session.execute(gh_stmt)
        integration_links = gh_result.scalars().all()

        existing_external_ids = {
            str(n.properties["external_id"])
            for n in node_dtos
            if n.properties and n.properties.get("external_id") is not None
        }
        now = datetime.now(tz=UTC)

        for link in integration_links:
            # Avoid duplicates if a real graph node already represents this link
            if str(link.external_id) in existing_external_ids:
                continue

            mapped_type = _GITHUB_NODE_TYPE_MAP.get(link.link_type, NodeType.NOTE.value)
            node_dtos.append(
                GraphNodeDTO(
                    # Deterministic ID from external_id so repeated fetches
                    # produce stable node IDs for frontend graph reconciliation.
                    id=str(uuid5(NAMESPACE_URL, f"ephemeral:{link.external_id}")),
                    node_type=mapped_type,
                    label=link.title or link.external_id,
                    summary=f"GitHub {link.link_type.value}: {link.title or link.external_id}",
                    properties={
                        "external_id": link.external_id,
                        "external_url": link.external_url,
                        "author_name": link.author_name,
                        "ephemeral": True,
                    },
                    created_at=now,
                    updated_at=now,
                    score=None,
                )
            )

    # Step 5: Sort by importance tier
    node_dtos.sort(key=lambda n: _node_tier(n.node_type))

    return GraphResponse(
        nodes=node_dtos,
        edges=edge_dtos,
        center_node_id=center_node_id,
    )


__all__ = ["issues_kg_router", "projects_kg_router", "router"]
