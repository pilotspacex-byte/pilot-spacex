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
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import select

from pilot_space.ai.agents.pilotspace_stream_utils import get_workspace_openai_key
from pilot_space.api.v1.schemas.knowledge_graph import (
    GraphEdgeDTO,
    GraphNodeDTO,
    GraphResponse,
)
from pilot_space.application.services.memory.graph_search_service import (
    GraphSearchPayload,
    GraphSearchService,
)
from pilot_space.dependencies.auth import SessionDep, SyncedUserId
from pilot_space.domain.graph_edge import EdgeType
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.database.models.integration import (
    IntegrationLink,
    IntegrationLinkType,
)
from pilot_space.infrastructure.database.models.issue import Issue as IssueModel
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

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
        summary=node.summary if node.content else None,
        properties=node.properties,  # type: ignore[arg-type]
        created_at=node.created_at,
        updated_at=node.updated_at,
        score=score,
    )


def _edge_to_dto(
    edge_id: UUID,
    source_id: UUID,
    target_id: UUID,
    edge_type: str,
    weight: float,
    properties: dict[str, object],
) -> GraphEdgeDTO:
    """Build a GraphEdgeDTO from edge fields."""
    try:
        label = _EDGE_LABELS[EdgeType(edge_type)]
    except ValueError:
        label = edge_type
    return GraphEdgeDTO(
        id=str(edge_id),
        source_id=str(source_id),
        target_id=str(target_id),
        edge_type=edge_type,
        label=label,
        weight=weight,
        properties=properties,
    )


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

    parsed_types: list[NodeType] | None = None
    if node_types:
        try:
            parsed_types = [NodeType(t.strip()) for t in node_types.split(",") if t.strip()]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid node_type: {exc}") from exc

    # Look up workspace OpenAI key for vector embedding (BYOK pattern)
    openai_api_key = await get_workspace_openai_key(session, workspace_id)

    repo = KnowledgeGraphRepository(session)
    service = GraphSearchService(repo)
    result = await service.execute(
        GraphSearchPayload(
            query=q,
            workspace_id=workspace_id,
            user_id=current_user_id,
            node_types=parsed_types,
            limit=limit,
            openai_api_key=openai_api_key,
        )
    )

    node_dtos = [_node_to_dto(sn.node, score=sn.score) for sn in result.nodes]
    edge_dtos = [
        _edge_to_dto(
            edge_id=e.id,
            source_id=e.source_id,
            target_id=e.target_id,
            edge_type=e.edge_type.value,
            weight=e.weight,
            properties=e.properties,  # type: ignore[arg-type]
        )
        for e in result.edges
    ]
    return GraphResponse(nodes=node_dtos, edges=edge_dtos)


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

    parsed_edge_types: list[EdgeType] | None = None
    if edge_types:
        try:
            parsed_edge_types = [EdgeType(t.strip()) for t in edge_types.split(",") if t.strip()]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid edge_type: {exc}") from exc

    repo = KnowledgeGraphRepository(session)
    neighbors = await repo.get_neighbors(
        node_id=node_id,
        edge_types=parsed_edge_types,
        depth=depth,
        workspace_id=workspace_id,
    )

    node_dtos = [_node_to_dto(n) for n in neighbors]
    return GraphResponse(nodes=node_dtos, edges=[], center_node_id=node_id)


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
    nodes, edges = await repo.get_subgraph(
        root_id=root_id,
        max_depth=max_depth,
        max_nodes=max_nodes,
        workspace_id=workspace_id,
    )

    node_dtos = [_node_to_dto(n) for n in nodes]
    edge_dtos = [
        _edge_to_dto(
            edge_id=e.id,
            source_id=e.source_id,
            target_id=e.target_id,
            edge_type=e.edge_type.value,
            weight=e.weight,
            properties=e.properties,  # type: ignore[arg-type]
        )
        for e in edges
    ]
    return GraphResponse(nodes=node_dtos, edges=edge_dtos, center_node_id=root_id)


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

_GITHUB_NODE_TYPE_MAP: dict[str, str] = {
    IntegrationLinkType.PULL_REQUEST: NodeType.PULL_REQUEST.value,
    IntegrationLinkType.BRANCH: NodeType.BRANCH.value,
    IntegrationLinkType.COMMIT: NodeType.CODE_REFERENCE.value,
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

    # Step 3: Extract subgraph from the graph node
    repo = KnowledgeGraphRepository(session)
    nodes, edges = await repo.get_subgraph(
        root_id=center_node_id,
        max_depth=depth,
        max_nodes=max_nodes,
        workspace_id=workspace_id,
    )

    # Apply node type filter if requested
    if node_types:
        allowed = {t.strip() for t in node_types.split(",") if t.strip()}
        nodes = [n for n in nodes if n.node_type.value in allowed]

    node_dtos = [_node_to_dto(n) for n in nodes]
    edge_dtos = [
        _edge_to_dto(
            edge_id=e.id,
            source_id=e.source_id,
            target_id=e.target_id,
            edge_type=e.edge_type.value,
            weight=e.weight,
            properties=e.properties,  # type: ignore[arg-type]
        )
        for e in edges
    ]

    # Step 4: Synthesize ephemeral GitHub nodes if requested
    if include_github:
        gh_stmt = select(IntegrationLink).where(
            IntegrationLink.issue_id == issue_id,
            IntegrationLink.workspace_id == workspace_id,
            IntegrationLink.is_deleted == False,  # noqa: E712
        )
        gh_result = await session.execute(gh_stmt)
        integration_links = gh_result.scalars().all()

        existing_external_ids = {n.properties.get("external_id") for n in node_dtos if n.properties}
        now = datetime.now(tz=UTC)

        for link in integration_links:
            # Avoid duplicates if a real graph node already represents this link
            if str(link.external_id) in existing_external_ids:
                continue

            mapped_type = _GITHUB_NODE_TYPE_MAP.get(link.link_type.value, "note")
            node_dtos.append(
                GraphNodeDTO(
                    id=str(uuid4()),
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


__all__ = ["issues_kg_router", "router"]
