"""Knowledge Graph REST API router.

Delegates to KnowledgeGraphQueryService and GraphSearchService.
Handles HTTP concerns: input parsing, RLS, DTO mapping, error translation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Path, Query, status
from sqlalchemy import select

from pilot_space.ai.agents.pilotspace_stream_utils import get_workspace_embedding_key
from pilot_space.api.v1.dependencies import KnowledgeGraphQueryServiceDep
from pilot_space.api.v1.repository_deps import IssueRepositoryDep, ProjectRepositoryDep
from pilot_space.api.v1.schemas.knowledge_graph import (
    GraphEdgeDTO,
    GraphNodeDTO,
    GraphResponse,
    RegenerateResponse,
)
from pilot_space.application.services.embedding_service import EmbeddingConfig, EmbeddingService
from pilot_space.application.services.memory.graph_search_service import (
    GraphSearchPayload,
    GraphSearchService,
)
from pilot_space.application.services.memory.knowledge_graph_query_service import (
    EntitySubgraphResult,
    EphemeralNode,
    node_tier,
)
from pilot_space.dependencies import QueueClientDep
from pilot_space.dependencies.auth import SessionDep, SyncedUserId, WorkspaceMemberId
from pilot_space.domain.exceptions import NotFoundError, ServiceUnavailableError, ValidationError
from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.infrastructure.database.models.cycle import Cycle as CycleModel
from pilot_space.infrastructure.database.models.issue import Issue as IssueModel
from pilot_space.infrastructure.database.models.note import Note as NoteModel
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.handlers.kg_populate_handler import TASK_KG_POPULATE
from pilot_space.infrastructure.queue.models import QueueName

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
        raise ValidationError(f"Invalid {param_name}: {exc}") from exc


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
    props = dict(node.properties or {})
    if node.external_id:
        props["external_id"] = str(node.external_id)
    return GraphNodeDTO(
        id=str(node.id),
        node_type=node.node_type.value,
        label=node.label,
        summary=node.summary or None,
        properties=props,
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

    openai_api_key = await get_workspace_embedding_key(session, workspace_id)
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

    result = await kg_service.get_subgraph(
        root_id=root_id,
        workspace_id=workspace_id,
        max_depth=max_depth,
        max_nodes=max_nodes,
    )

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
# Workspace overview endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/overview",
    response_model=GraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Workspace knowledge graph overview",
    description=(
        "Return all nodes and edges in the workspace knowledge graph, "
        "ordered by recency and capped at max_nodes. "
        "Use for the workspace-level graph visualization page."
    ),
)
async def get_workspace_overview(
    workspace_id: WorkspaceIdPath,
    session: SessionDep,
    current_user_id: SyncedUserId,
    _member: WorkspaceMemberId,
    node_types: Annotated[
        str | None,
        Query(description="Comma-separated NodeType values to filter by"),
    ] = None,
    max_nodes: Annotated[int, Query(ge=5, le=500, description="Maximum nodes")] = 200,
) -> GraphResponse:
    """Return workspace-wide knowledge graph overview with nodes and edges."""
    await set_rls_context(session, current_user_id, workspace_id)

    parsed_types: list[NodeType] | None = _parse_csv_enum(node_types, NodeType, "node_type")

    repo = KnowledgeGraphRepository(session)
    nodes, edges = await repo.get_workspace_overview(
        workspace_id=workspace_id,
        max_nodes=max_nodes,
        node_types=parsed_types,
    )

    node_dtos = [_node_to_dto(n) for n in nodes]
    node_dtos.sort(key=lambda n: node_tier(n.node_type))

    return GraphResponse(nodes=node_dtos, edges=_edges_to_dtos(edges))


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

    result = await kg_service.get_issue_knowledge_graph(
        issue_id=issue_id,
        workspace_id=workspace_id,
        depth=depth,
        node_types=node_types,
        max_nodes=max_nodes,
        include_github=include_github,
    )

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

    result = await kg_service.get_project_knowledge_graph(
        project_id=project_id,
        workspace_id=workspace_id,
        depth=depth,
        node_types=node_types,
        max_nodes=max_nodes,
        include_github=include_github,
    )

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


_regen_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# KG populate payload helper
# ---------------------------------------------------------------------------


def _build_kg_payload(
    entity_type: str,
    entity_id: UUID,
    workspace_id: UUID,
    project_id: UUID,
    actor_user_id: UUID,
) -> dict[str, str]:
    """Build a kg_populate queue message payload."""
    return {
        "task_type": TASK_KG_POPULATE,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "workspace_id": str(workspace_id),
        "actor_user_id": str(actor_user_id),
        "project_id": str(project_id),
    }


# ---------------------------------------------------------------------------
# Regeneration endpoints
# ---------------------------------------------------------------------------


@issues_kg_router.post(
    "/issues/{issue_id}/knowledge-graph/regenerate",
    response_model=RegenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Regenerate issue knowledge graph",
    description=(
        "Re-enqueue a kg_populate job for a single issue. "
        "Use when the issue's graph node is missing or stale."
    ),
)
async def regenerate_issue_knowledge_graph(
    workspace_id: WorkspaceIdPath,
    issue_id: Annotated[UUID, Path(description="Issue UUID")],
    session: SessionDep,
    current_user_id: SyncedUserId,
    _member: WorkspaceMemberId,
    issue_repo: IssueRepositoryDep,
    queue_client: QueueClientDep,
) -> RegenerateResponse:
    """Re-enqueue kg_populate for a single issue."""
    await set_rls_context(session, current_user_id, workspace_id)

    if queue_client is None:
        raise ServiceUnavailableError("Queue service unavailable")

    issue = await issue_repo.get_by_id(issue_id)
    if issue is None or issue.is_deleted:
        raise NotFoundError("Issue not found")
    if issue.workspace_id != workspace_id:
        raise NotFoundError("Issue not found")

    await queue_client.enqueue(
        QueueName.AI_NORMAL,
        _build_kg_payload("issue", issue.id, issue.workspace_id, issue.project_id, current_user_id),
    )
    _regen_logger.info(
        "kg_regenerate_issue",
        issue_id=str(issue_id),
        workspace_id=str(workspace_id),
    )
    return RegenerateResponse(enqueued=1, detail=f"Enqueued kg_populate for issue {issue_id}")


@projects_kg_router.post(
    "/projects/{project_id}/knowledge-graph/regenerate",
    response_model=RegenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Regenerate project knowledge graph",
    description=(
        "Re-enqueue kg_populate jobs for a project and all its issues, notes, "
        "and cycles. Use to backfill an empty knowledge graph."
    ),
)
async def regenerate_project_knowledge_graph(
    workspace_id: WorkspaceIdPath,
    project_id: Annotated[UUID, Path(description="Project UUID")],
    session: SessionDep,
    current_user_id: SyncedUserId,
    _member: WorkspaceMemberId,
    project_repo: ProjectRepositoryDep,
    queue_client: QueueClientDep,
) -> RegenerateResponse:
    """Re-enqueue kg_populate for a project and all its child entities."""
    await set_rls_context(session, current_user_id, workspace_id)

    if queue_client is None:
        raise ServiceUnavailableError("Queue service unavailable")

    project = await project_repo.get_by_id(project_id)
    if project is None or project.is_deleted:
        raise NotFoundError("Project not found")
    if project.workspace_id != workspace_id:
        raise NotFoundError("Project not found")

    enqueued = 0

    # 1. Enqueue the project itself
    await queue_client.enqueue(
        QueueName.AI_NORMAL,
        _build_kg_payload("project", project_id, project.workspace_id, project_id, current_user_id),
    )
    enqueued += 1

    # 2. Enqueue all non-deleted issues in this project
    issue_rows = await session.execute(
        select(IssueModel.id).where(
            IssueModel.project_id == project_id,
            IssueModel.is_deleted == False,  # noqa: E712
        )
    )
    for (issue_id,) in issue_rows.all():
        await queue_client.enqueue(
            QueueName.AI_NORMAL,
            _build_kg_payload("issue", issue_id, project.workspace_id, project_id, current_user_id),
        )
        enqueued += 1

    # 3. Enqueue all non-deleted notes in this project
    note_rows = await session.execute(
        select(NoteModel.id).where(
            NoteModel.project_id == project_id,
            NoteModel.is_deleted == False,  # noqa: E712
        )
    )
    for (note_id,) in note_rows.all():
        await queue_client.enqueue(
            QueueName.AI_NORMAL,
            _build_kg_payload("note", note_id, project.workspace_id, project_id, current_user_id),
        )
        enqueued += 1

    # 4. Enqueue all non-deleted cycles in this project
    cycle_rows = await session.execute(
        select(CycleModel.id).where(
            CycleModel.project_id == project_id,
            CycleModel.is_deleted == False,  # noqa: E712
        )
    )
    for (cycle_id,) in cycle_rows.all():
        await queue_client.enqueue(
            QueueName.AI_NORMAL,
            _build_kg_payload("cycle", cycle_id, project.workspace_id, project_id, current_user_id),
        )
        enqueued += 1

    _regen_logger.info(
        "kg_regenerate_project",
        project_id=str(project_id),
        workspace_id=str(workspace_id),
        enqueued=enqueued,
    )
    return RegenerateResponse(
        enqueued=enqueued,
        detail=f"Enqueued {enqueued} kg_populate jobs for project {project_id}",
    )


__all__ = ["issues_kg_router", "projects_kg_router", "router"]
