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
from sqlalchemy import text

from pilot_space.api.v1.dependencies import NoteRepositoryDep, WorkspaceRepositoryDep
from pilot_space.dependencies.auth import SessionDep, SyncedUserId
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )


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
    _current_user: SyncedUserId,
) -> Response:
    await _validate_note_access(workspace_id, note_id, workspace_repo, note_repo)

    result = await session.execute(
        text("SELECT state FROM note_yjs_states WHERE note_id = :note_id"),
        {"note_id": str(note_id)},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Yjs state persisted for this note",
        )

    logger.debug(
        "[YjsState] GET note_id=%s state_bytes=%d",
        note_id,
        len(row[0]),
    )

    return Response(
        content=bytes(row[0]),
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
    _current_user: SyncedUserId,
) -> Response:
    await _validate_note_access(workspace_id, note_id, workspace_repo, note_repo)

    body = await request.body()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request body must be non-empty Yjs state bytes",
        )

    # Upsert: insert or replace on conflict
    await session.execute(
        text("""
            INSERT INTO note_yjs_states (note_id, state, updated_at)
            VALUES (:note_id, :state, now())
            ON CONFLICT (note_id)
            DO UPDATE SET state = EXCLUDED.state, updated_at = now()
        """),
        {"note_id": str(note_id), "state": body},
    )
    await session.commit()

    logger.debug(
        "[YjsState] PUT note_id=%s state_bytes=%d",
        note_id,
        len(body),
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
