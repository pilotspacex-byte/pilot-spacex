"""Related Issues API router -- semantic suggestions, manual linking, and dismissal.

Phase 15: RELISS-01..04

Routes:
- GET  /{workspace_id}/issues/{issue_id}/related-suggestions
- POST /{workspace_id}/issues/{issue_id}/related-suggestions/{target_issue_id}/dismiss
- POST /{workspace_id}/issues/{issue_id}/relations
- DELETE /{workspace_id}/issues/{issue_id}/relations/{link_id}

Thin HTTP shell -- suggestion logic delegated to RelatedIssuesSuggestionService.
Manual linking and dismissal remain in router (thin CRUD, no complex business logic).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError

from pilot_space.api.v1.dependencies import (
    RelatedIssuesSuggestionServiceDep,
    WorkspaceRepositoryDep,
)
from pilot_space.api.v1.repository_deps import IssueLinkRepositoryDep
from pilot_space.api.v1.schemas.related_issues import (
    IssueLinkCreateRequest,
    IssueLinkCreateResponse,
    RelatedSuggestion,
)
from pilot_space.dependencies import SyncedUserId
from pilot_space.dependencies.auth import SessionDep
from pilot_space.infrastructure.database.models.issue_link import IssueLink, IssueLinkType
from pilot_space.infrastructure.database.rls import set_rls_context

router = APIRouter(tags=["related-issues"])

WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace UUID or slug")]
IssueIdPath = Annotated[UUID, Path(description="Issue UUID")]


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
# RELISS-01: Semantic suggestions (delegated to service)
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
    service: RelatedIssuesSuggestionServiceDep,
) -> list[RelatedSuggestion]:
    """Return semantically related issue suggestions for a given issue."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    results = await service.suggest_related(
        workspace_id=workspace.id,
        issue_id=issue_id,
        user_id=current_user_id,
    )
    return [
        RelatedSuggestion(
            id=r.id,
            title=r.title,
            identifier=r.identifier,
            similarity_score=r.similarity_score,
            reason=r.reason,
        )
        for r in results
    ]


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
    """Dismiss a related issue suggestion for the current user."""
    from pilot_space.infrastructure.database.repositories.issue_suggestion_dismissal_repository import (
        IssueSuggestionDismissalRepository,
    )

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
    """Create a RELATED link between two issues."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

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
    """Soft-delete an issue relation link."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    link = await link_repo.get_by_id(link_id)
    if link is None or link.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relation not found")

    await link_repo.delete(link)
