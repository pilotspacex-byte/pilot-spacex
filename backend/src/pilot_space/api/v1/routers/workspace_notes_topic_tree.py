"""Workspace-scoped Topic-tree API router (Phase 93 Plan 02).

Three endpoints under ``/api/v1/workspaces/{workspace_id}/notes/{note_id}/...``:

  * ``GET  /children``  — paginated direct topic children
  * ``GET  /ancestors`` — root → leaf chain (incl. self)
  * ``POST /move``      — reparent a topic; max-depth + cycle invariants

Extracted as a sibling router (mounted at the same ``/workspaces`` prefix) to
keep ``workspace_notes.py`` under the 700-line pre-commit cap. URL structure
is identical to ``workspace_notes.py`` — clients see one cohesive surface.

Per ``service-pattern.md`` + ``exception-handler.md``, the router is a thin
shell: ``TopicTreeService`` raises typed domain exceptions
(``TopicCycleError`` / ``TopicMaxDepthExceededError`` / ``ForbiddenError`` /
``NotFoundError``) which propagate to the global ``app_error_handler`` that
emits ``application/problem+json`` (RFC 7807). NO try/except around service
calls in this module.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from pilot_space.api.v1.dependencies import (
    TopicTreeServiceDep,
    WorkspaceRepositoryDep,
)
from pilot_space.api.v1.schemas.base import PaginatedResponse
from pilot_space.api.v1.schemas.note import MoveTopicRequest, NoteResponse
from pilot_space.application.services.note import GetChildrenPayload
from pilot_space.dependencies.auth import CurrentUserId, SessionDep
from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

topic_tree_router = APIRouter()

# Shared path aliases (re-declared per workspace_note_annotations.py pattern).
WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace ID (UUID) or slug")]
NoteIdPath = Annotated[UUID, Path(description="Note ID")]


def _is_valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def _resolve_workspace(
    workspace_id_or_slug: str,
    workspace_repo: WorkspaceRepositoryDep,
) -> Workspace:
    """Resolve workspace by UUID or slug, 404 if not found."""
    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id_scalar(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug_scalar(workspace_id_or_slug)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


def _note_to_response(note: Note) -> NoteResponse:
    """Convert Note ORM to NoteResponse including topic-tree fields.

    Adds ``parent_topic_id`` and ``topic_depth`` (Phase 93) so the tree UI can
    render indentation + restore parent links without an extra round-trip.
    """
    return NoteResponse(
        id=note.id,
        created_at=note.created_at,
        updated_at=note.updated_at,
        workspace_id=note.workspace_id,
        project_id=note.project_id,
        title=note.title,
        is_pinned=note.is_pinned,
        word_count=note.word_count,
        last_edited_by_id=note.owner_id,
        icon_emoji=note.icon_emoji,
        parent_topic_id=note.parent_topic_id,
        topic_depth=note.topic_depth,
    )


# ── GET /children ────────────────────────────────────────────────────────────


@topic_tree_router.get(
    "/{workspace_id}/notes/{note_id}/children",
    response_model=PaginatedResponse[NoteResponse],
    tags=["topics"],
    summary="List direct topic children of a note",
)
async def list_topic_children(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    topic_tree: TopicTreeServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> PaginatedResponse[NoteResponse]:
    """List direct topic children of ``note_id`` in this workspace."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    result = await topic_tree.get_children(
        GetChildrenPayload(
            workspace_id=workspace.id,
            parent_topic_id=note_id,
            page=page,
            page_size=page_size,
        )
    )

    items = [_note_to_response(n) for n in result.rows]
    has_next = (page * page_size) < result.total
    has_prev = page > 1
    return PaginatedResponse(
        items=items,
        total=result.total,
        next_cursor=str(page + 1) if has_next else None,
        prev_cursor=str(page - 1) if has_prev else None,
        has_next=has_next,
        has_prev=has_prev,
        page_size=page_size,
    )


# ── GET /ancestors ───────────────────────────────────────────────────────────


@topic_tree_router.get(
    "/{workspace_id}/notes/{note_id}/ancestors",
    response_model=list[NoteResponse],
    tags=["topics"],
    summary="List topic ancestors (root → leaf, including self)",
)
async def list_topic_ancestors(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    topic_tree: TopicTreeServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> list[NoteResponse]:
    """Walk parent chain root → leaf for ``note_id``. Empty list if missing."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    rows = await topic_tree.get_ancestors(note_id)
    return [_note_to_response(n) for n in rows]


# ── POST /move ───────────────────────────────────────────────────────────────


@topic_tree_router.post(
    "/{workspace_id}/notes/{note_id}/move",
    response_model=NoteResponse,
    tags=["topics"],
    summary="Move a topic under a new parent (or to root)",
)
async def move_topic(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    payload: MoveTopicRequest,
    current_user_id: CurrentUserId,
    topic_tree: TopicTreeServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> NoteResponse:
    """Reparent ``note_id`` under ``payload.parent_id`` (root if None).

    Service raises typed domain exceptions on cycle / max-depth / cross-
    workspace / not-found which propagate to the global RFC 7807 handler.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    updated = await topic_tree.move_topic(note_id, payload.parent_id)
    # Repository owns the savepoint; commit the outer transaction so the
    # caller-visible state matches the move outcome.
    await session.commit()

    logger.info(
        "topic_moved",
        extra={
            "topic_id": str(note_id),
            "new_parent_id": str(payload.parent_id) if payload.parent_id else None,
            "workspace_id": str(workspace.id),
        },
    )
    return _note_to_response(updated)
