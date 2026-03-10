"""Related Issues API router — semantic suggestions, manual linking, and dismissal.

Phase 15: RELISS-01..04

Routes:
- GET  /{workspace_id}/issues/{issue_id}/related-suggestions
- POST /{workspace_id}/issues/{issue_id}/related-suggestions/{target_issue_id}/dismiss
- POST /{workspace_id}/issues/{issue_id}/relations
- DELETE /{workspace_id}/issues/{issue_id}/relations/{link_id}
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from pilot_space.api.v1.dependencies import WorkspaceRepositoryDep
from pilot_space.api.v1.repository_deps import IssueLinkRepositoryDep
from pilot_space.dependencies import SyncedUserId
from pilot_space.dependencies.auth import SessionDep
from pilot_space.domain.graph_node import NodeType
from pilot_space.infrastructure.database.models.issue import Issue
from pilot_space.infrastructure.database.models.issue_link import IssueLink, IssueLinkType
from pilot_space.infrastructure.database.repositories.issue_suggestion_dismissal_repository import (
    IssueSuggestionDismissalRepository,
)
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["related-issues"])

WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace UUID or slug")]
IssueIdPath = Annotated[UUID, Path(description="Issue UUID")]


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class RelatedSuggestion(BaseModel):
    """Semantic suggestion for a related issue."""

    id: UUID
    title: str
    identifier: str
    similarity_score: float
    reason: str


class IssueLinkCreateRequest(BaseModel):
    """Request body for creating an issue relation."""

    target_issue_id: UUID
    link_type: Literal["related"] = "related"


class IssueLinkCreateResponse(BaseModel):
    """Response schema for a newly created issue relation."""

    id: UUID
    source_issue_id: UUID
    target_issue_id: UUID
    link_type: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _resolve_workspace(workspace_id: str, workspace_repo: WorkspaceRepositoryDep):  # type: ignore[return]
    """Resolve workspace by UUID or slug. Raises 404 if not found."""
    import uuid as _uuid

    try:
        ws_uuid = _uuid.UUID(workspace_id)
        workspace = await workspace_repo.get_by_id(ws_uuid)
    except ValueError:
        workspace = await workspace_repo.get_by_slug(workspace_id)

    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


# ---------------------------------------------------------------------------
# RELISS-01: Semantic suggestions
# ---------------------------------------------------------------------------


@router.get(
    "/{workspace_id}/issues/{issue_id}/related-suggestions",
    response_model=list[RelatedSuggestion],
    tags=["related-issues"],
    summary="Get semantically related issue suggestions",
)
async def get_related_suggestions(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
) -> list[RelatedSuggestion]:
    """Return semantically related issue suggestions for a given issue.

    Returns empty list when the issue has no knowledge graph node yet
    (kg_populate not yet run). Never returns the source issue itself.
    Dismissed suggestions are excluded.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    kg_repo = KnowledgeGraphRepository(session)
    dismissal_repo = IssueSuggestionDismissalRepository(session)

    # Find the issue's KG node
    node = await kg_repo._find_node_by_external(  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        workspace.id, NodeType.ISSUE, issue_id
    )
    if node is None:
        return []

    # Hybrid search for related issues (overfetch for filtering)
    scored_nodes = await kg_repo.hybrid_search(
        query_embedding=node.embedding,
        query_text=node.content or "",
        workspace_id=workspace.id,
        node_types=[NodeType.ISSUE],
        limit=13,
    )

    # Get dismissed target IDs for this user/issue pair
    dismissed_ids = await dismissal_repo.get_dismissed_target_ids(current_user_id, issue_id)

    # Filter: exclude self and dismissed
    candidates = [
        sn
        for sn in scored_nodes
        if sn.node.external_id != issue_id and sn.node.external_id not in dismissed_ids
    ][:8]

    if not candidates:
        return []

    # Batch-fetch issue records for enrichment
    candidate_issue_ids = [sn.node.external_id for sn in candidates if sn.node.external_id]
    issues_result = await session.execute(
        select(Issue).where(
            Issue.id.in_(candidate_issue_ids),
            Issue.is_deleted == False,  # noqa: E712
        )
    )
    issues_by_id: dict[UUID, Issue] = {issue.id: issue for issue in issues_result.scalars().all()}

    # Enrich reasons via KG edges
    candidate_node_ids = [sn.node.id for sn in candidates if sn.node.id]
    edges = await kg_repo.get_edges_between(
        candidate_node_ids + ([node.id] if node.id else []),
        workspace.id,
    )

    # Map node_id -> set of connected node_ids for edge lookup
    from pilot_space.domain.graph_edge import EdgeType

    shared_note_node_ids: set[UUID] = set()
    same_project_node_ids: set[UUID] = set()
    for edge in edges:
        if edge.edge_type == EdgeType.BELONGS_TO:
            same_project_node_ids.add(edge.source_id)
            same_project_node_ids.add(edge.target_id)
        elif edge.edge_type == EdgeType.RELATES_TO:
            shared_note_node_ids.add(edge.source_id)
            shared_note_node_ids.add(edge.target_id)

    suggestions: list[RelatedSuggestion] = []
    for scored_node in candidates:
        ext_id = scored_node.node.external_id
        if ext_id is None:
            continue
        issue_rec = issues_by_id.get(ext_id)
        if issue_rec is None:
            continue

        # Determine reason
        node_id = scored_node.node.id
        if node_id in same_project_node_ids:
            reason = "same project"
        elif node_id in shared_note_node_ids:
            reason = "shared note"
        else:
            reason = f"Semantic match ({round(scored_node.score * 100)}%)"

        suggestions.append(
            RelatedSuggestion(
                id=issue_rec.id,
                title=issue_rec.name,
                identifier=issue_rec.identifier,
                similarity_score=scored_node.score,
                reason=reason,
            )
        )

    return suggestions


# ---------------------------------------------------------------------------
# RELISS-04: Dismissal
# ---------------------------------------------------------------------------


@router.post(
    "/{workspace_id}/issues/{issue_id}/related-suggestions/{target_issue_id}/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["related-issues"],
    summary="Dismiss a related issue suggestion",
)
async def dismiss_suggestion(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    target_issue_id: Annotated[UUID, Path(description="Target issue UUID to dismiss")],
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
) -> None:
    """Dismiss a related issue suggestion for the current user.

    Idempotent: returns 204 even if already dismissed (UNIQUE constraint
    catches duplicates and is treated as a no-op).
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    dismissal_repo = IssueSuggestionDismissalRepository(session)
    try:
        await dismissal_repo.create_dismissal(
            workspace_id=workspace.id,
            user_id=current_user_id,
            source_issue_id=issue_id,
            target_issue_id=target_issue_id,
        )
    except IntegrityError:
        # Already dismissed — treat as no-op (idempotent)
        await session.rollback()


# ---------------------------------------------------------------------------
# RELISS-02: Manual relation create / delete
# ---------------------------------------------------------------------------


@router.post(
    "/{workspace_id}/issues/{issue_id}/relations",
    response_model=IssueLinkCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["related-issues"],
    summary="Create a manual issue relation",
)
async def create_issue_relation(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    body: IssueLinkCreateRequest,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    link_repo: IssueLinkRepositoryDep,
) -> IssueLinkCreateResponse:
    """Create a RELATED link between two issues.

    Returns 409 if the relation already exists in either direction.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    # Bidirectional duplicate check
    if await link_repo.link_exists(
        issue_id, body.target_issue_id, IssueLinkType.RELATED, workspace.id
    ) or await link_repo.link_exists(
        body.target_issue_id, issue_id, IssueLinkType.RELATED, workspace.id
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Relation already exists")

    link_id = uuid4()
    link = IssueLink(
        id=link_id,
        workspace_id=workspace.id,
        source_issue_id=issue_id,
        target_issue_id=body.target_issue_id,
        link_type=IssueLinkType.RELATED,
    )
    session.add(link)
    await session.flush()
    return IssueLinkCreateResponse(
        id=link_id,
        source_issue_id=issue_id,
        target_issue_id=body.target_issue_id,
        link_type=IssueLinkType.RELATED.value,
    )


@router.delete(
    "/{workspace_id}/issues/{issue_id}/relations/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["related-issues"],
    summary="Delete (soft-delete) an issue relation",
)
async def delete_issue_relation(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    link_id: Annotated[UUID, Path(description="Issue link UUID")],
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    link_repo: IssueLinkRepositoryDep,
) -> None:
    """Soft-delete an issue relation link. Returns 404 if not found in workspace."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    link = await link_repo.get_by_id(link_id)
    if link is None or link.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relation not found")

    await link_repo.delete(link)
