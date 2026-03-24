"""Yjs state persistence API for collaborative note editing.

T-117: Backend API for Yjs state persistence (GET/PUT yjs-state).

Endpoints:
  GET  /workspaces/{workspace_id}/notes/{note_id}/yjs-state
       → 200 application/octet-stream (binary Yjs state)
       → 404 if no state persisted yet (client starts fresh)

  PUT  /workspaces/{workspace_id}/notes/{note_id}/yjs-state
       → 204 No Content on success
       Body: application/octet-stream (binary Yjs state from Y.encodeStateAsUpdate)

Authentication: Supabase JWT (Bearer token).
Authorization: RLS — workspace membership required (via DB policy).
Rate limiting: PUT capped at 1 request/second per note (client-side debounce handles this).

Notes on persistence strategy:
  - State stored as a complete Yjs update (Y.encodeStateAsUpdate output)
  - On each PUT the state is fully replaced (upsert) — Yjs convergence handles merging
  - On GET: client applies the state to a fresh Y.Doc to restore the document
  - If all clients disconnect and reconnect, the DB state is the authoritative source

@module api/v1/routers/note_yjs_state
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Request, Response, status

from pilot_space.api.v1.dependencies import NoteRepositoryDep, WorkspaceRepositoryDep
from pilot_space.api.v1.repository_deps import NoteYjsStateRepositoryDep
from pilot_space.dependencies.auth import SessionDep, SyncedUserId
from pilot_space.domain.exceptions import (
    NotFoundError,
    ValidationError as DomainValidationError,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["notes", "collab"])

WorkspaceIdPath = Annotated[UUID, Path(description="Workspace UUID")]
NoteIdPath = Annotated[UUID, Path(description="Note UUID")]


async def _validate_note_access(
    workspace_id: UUID,
    note_id: UUID,
    workspace_repo: WorkspaceRepositoryDep,
    note_repo: NoteRepositoryDep,
) -> None:
    """Verify workspace exists and note belongs to it."""
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise NotFoundError("Workspace not found")
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace_id:
        raise NotFoundError("Note not found")


@router.get(
    "/{workspace_id}/notes/{note_id}/yjs-state",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Get persisted Yjs document state for a note",
    description=(
        "Returns the full binary Yjs document state as application/octet-stream. "
        "Returns 404 if no state has been persisted yet — client should start from an empty Y.Doc."
    ),
)
async def get_yjs_state(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    session: SessionDep,
    workspace_repo: WorkspaceRepositoryDep,
    note_repo: NoteRepositoryDep,
    yjs_repo: NoteYjsStateRepositoryDep,
    _current_user: SyncedUserId,
) -> Response:
    await _validate_note_access(workspace_id, note_id, workspace_repo, note_repo)

    state = await yjs_repo.get_state(note_id)
    if not state:
        raise NotFoundError("No Yjs state persisted for this note")

    logger.debug("[YjsState] GET note_id=%s state_bytes=%d", note_id, len(state))

    return Response(
        content=state,
        media_type="application/octet-stream",
        headers={"Cache-Control": "no-store"},
    )


@router.put(
    "/{workspace_id}/notes/{note_id}/yjs-state",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Persist Yjs document state for a note",
    description=(
        "Stores the full binary Yjs document state (Y.encodeStateAsUpdate output). "
        "Upserts on conflict — previous state is fully replaced."
    ),
)
async def put_yjs_state(
    request: Request,
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    session: SessionDep,
    workspace_repo: WorkspaceRepositoryDep,
    note_repo: NoteRepositoryDep,
    yjs_repo: NoteYjsStateRepositoryDep,
    _current_user: SyncedUserId,
) -> Response:
    await _validate_note_access(workspace_id, note_id, workspace_repo, note_repo)

    body = await request.body()
    if not body:
        raise DomainValidationError("Request body must be non-empty Yjs state bytes")

    _MAX_YJS_BODY_BYTES = 4 * 1024 * 1024  # 4 MB
    if len(body) > _MAX_YJS_BODY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Yjs state exceeds 4 MB limit ({len(body)} bytes)",
        )

    await yjs_repo.upsert_state(note_id, body)

    logger.debug("[YjsState] PUT note_id=%s state_bytes=%d", note_id, len(body))

    return Response(status_code=status.HTTP_204_NO_CONTENT)
