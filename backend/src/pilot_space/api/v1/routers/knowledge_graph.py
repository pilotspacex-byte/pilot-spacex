"""Knowledge Graph REST API router.

Thin router that delegates all business logic to KnowledgeGraphQueryService
and GraphSearchService. Only handles HTTP concerns: input parsing,
RLS context, DTO mapping, and error translation.

Endpoints:
  GET  /api/v1/workspaces/{workspace_id}/knowledge-graph/search
  GET  /api/v1/workspaces/{workspace_id}/knowledge-graph/nodes/{node_id}/neighbors
  GET  /api/v1/workspaces/{workspace_id}/knowledge-graph/subgraph
  GET  /api/v1/workspaces/{workspace_id}/knowledge-graph/user-context
  GET  /api/v1/workspaces/{workspace_id}/issues/{issue_id}/knowledge-graph
  GET  /api/v1/workspaces/{workspace_id}/projects/{project_id}/knowledge-graph

Feature 016: Knowledge Graph — Unit 7 REST API
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from pilot_space.ai.agents.pilotspace_stream_utils import get_workspace_openai_key
from pilot_space.api.v1.dependencies import KnowledgeGraphQueryServiceDep
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
from pilot_space.application.services.memory.knowledge_graph_query_service import (
    EntityNotFoundError,
    EntitySubgraphResult,
    EphemeralNode,
    RootNodeNotFoundError,
    node_tier,
)
from pilot_space.dependencies.auth import SessionDep, SyncedUserId
from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context

_EnumT = TypeVar("_EnumT", bound=StrEnum)


def _parse_csv_enum(
    raw: str | None,
    enum_cls: type[_EnumT],
    param_name: str,
) -> list[_EnumT] | None:
    """Parse a comma-separated enum string into a list of enum values."""
    if not raw:
        return None
    try:
        return [enum_cls(t.strip()) for t in raw.split(",") if t.strip()]  # type: ignore[call-arg]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {param_name}: {exc}") from exc


# ---------------------------------------------------------------------------
# Edge labels for DTO mapping
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


# ---------------------------------------------------------------------------
# Domain → DTO mappers (presentation layer concern)
# ---------------------------------------------------------------------------


def _node_to_dto(node: GraphNode, score: float | None = None) -> GraphNodeDTO:
    """Map a domain GraphNode to a GraphNodeDTO."""
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


def _ephemeral_to_dto(node: EphemeralNode) -> GraphNodeDTO:
    """Map an ephemeral GitHub node to a GraphNodeDTO."""
    return GraphNodeDTO(
        id=node.id,
        node_type=node.node_type,
        label=node.label,
        summary=node.summary,
        properties=node.properties,
        created_at=node.created_at,
        updated_at=node.updated_at,
        score=None,
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/workspaces/{workspace_id}/knowledge-graph",
    tags=["knowledge-graph"],
)

issues_kg_router = APIRouter(
    prefix="/workspaces/{workspace_id}",
    tags=["knowledge-graph"],
)

projects_kg_router = APIRouter(
    prefix="/workspaces/{workspace_id}",
    tags=["knowledge-graph"],
)

WorkspaceIdPath = Annotated[UUID, Path(description="Workspace UUID")]


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
    kg_service: KnowledgeGraphQueryServiceDep,
    depth: Annotated[int, Query(ge=1, le=4, description="Traversal depth")] = 1,
    edge_types: Annotated[
        str | None,
        Query(description="Comma-separated EdgeType values to restrict traversal"),
    ] = None,
) -> GraphResponse:
    """Return local neighborhood subgraph around the given node."""
    await set_rls_context(session, current_user_id, workspace_id)

    parsed_edge_types: list[EdgeType] | None = _parse_csv_enum(edge_types, EdgeType, "edge_type")

    result = await kg_service.get_neighbors(
        node_id=node_id,
        workspace_id=workspace_id,
        depth=depth,
        edge_types=parsed_edge_types,
    )

    node_dtos = [_node_to_dto(n) for n in result.nodes]
    return GraphResponse(
        nodes=node_dtos, edges=_edges_to_dtos(result.edges), center_node_id=node_id
    )


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
    kg_service: KnowledgeGraphQueryServiceDep,
    root_id: Annotated[UUID, Query(description="Root node UUID")],
    max_depth: Annotated[int, Query(ge=1, le=4, description="Maximum traversal depth")] = 2,
    max_nodes: Annotated[int, Query(ge=5, le=100, description="Maximum node count")] = 50,
) -> GraphResponse:
    """Extract a subgraph for visualization centered on root_id."""
    await set_rls_context(session, current_user_id, workspace_id)

    try:
        result = await kg_service.get_subgraph(
            root_id=root_id,
            workspace_id=workspace_id,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )
    except RootNodeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Root node not found"
        ) from exc

    node_dtos = [_node_to_dto(n) for n in result.nodes]
    return GraphResponse(
        nodes=node_dtos, edges=_edges_to_dtos(result.edges), center_node_id=root_id
    )


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
    kg_service: KnowledgeGraphQueryServiceDep,
    limit: Annotated[int, Query(ge=1, le=50, description="Maximum nodes")] = 10,
) -> GraphResponse:
    """Return personal context nodes for the current user."""
    await set_rls_context(session, current_user_id, workspace_id)

    result = await kg_service.get_user_context(
        workspace_id=workspace_id,
        user_id=current_user_id,
        limit=limit,
    )

    node_dtos = [_node_to_dto(n) for n in result.nodes]
    return GraphResponse(nodes=node_dtos, edges=[])


# ---------------------------------------------------------------------------
# Issue-scoped endpoint
# ---------------------------------------------------------------------------


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
    kg_service: KnowledgeGraphQueryServiceDep,
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
    _parse_csv_enum(node_types, NodeType, "node_type")

    try:
        result = await kg_service.get_issue_knowledge_graph(
            issue_id=issue_id,
            workspace_id=workspace_id,
            depth=depth,
            node_types=node_types,
            max_nodes=max_nodes,
            include_github=include_github,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found"
        ) from exc

    return _entity_result_to_response(result)


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
    kg_service: KnowledgeGraphQueryServiceDep,
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
    _parse_csv_enum(node_types, NodeType, "node_type")

    try:
        result = await kg_service.get_project_knowledge_graph(
            project_id=project_id,
            workspace_id=workspace_id,
            depth=depth,
            node_types=node_types,
            max_nodes=max_nodes,
            include_github=include_github,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from exc

    return _entity_result_to_response(result)


# ---------------------------------------------------------------------------
# Shared response builder for entity-scoped endpoints
# ---------------------------------------------------------------------------


def _entity_result_to_response(result: EntitySubgraphResult) -> GraphResponse:
    """Convert an EntitySubgraphResult to a GraphResponse with ephemeral nodes merged."""

    node_dtos = [_node_to_dto(n) for n in result.nodes]
    edge_dtos = _edges_to_dtos(result.edges)

    for en in result.ephemeral_nodes:
        node_dtos.append(_ephemeral_to_dto(en))

    # Sort after merging so ephemeral nodes land in their correct tier position
    node_dtos.sort(key=lambda n: node_tier(n.node_type))

    return GraphResponse(nodes=node_dtos, edges=edge_dtos, center_node_id=result.center_node_id)


__all__ = ["issues_kg_router", "projects_kg_router", "router"]
