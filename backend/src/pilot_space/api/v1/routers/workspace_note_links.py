"""Workspace-scoped Note-to-Note Link API router.

Provides REST endpoints for creating and managing note-to-note links.
Supports wiki-style [[links]] and /link-note block embeds.

Routes:
- POST   /{workspace_id}/notes/{note_id}/links          — Create note link (idempotent)
- DELETE /{workspace_id}/notes/{note_id}/links/{target}  — Remove note link
- GET    /{workspace_id}/notes/{note_id}/links           — List outgoing links
- GET    /{workspace_id}/notes/{note_id}/backlinks       — List backlinks
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import Field

from pilot_space.api.v1.dependencies import (
    NoteRepositoryDep,
)
from pilot_space.api.v1.repository_deps import NoteNoteLinkRepositoryDep
from pilot_space.api.v1.schemas.base import BaseSchema
from pilot_space.dependencies.auth import CurrentUserId, SessionDep
from pilot_space.infrastructure.database.models.note_note_link import (
    NoteNoteLink,
    NoteNoteLinkType,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CreateNoteLinkRequest(BaseSchema):
    """Request body for POST /{wid}/notes/{nid}/links."""

    target_note_id: UUID = Field(description="Target note UUID to link to")
    link_type: Literal["inline", "embed"] = Field(
        default="inline",
        description="Link type: inline (wiki-style) or embed (block)",
    )
    block_id: str | None = Field(
        default=None,
        description="TipTap block ID where the link originates",
    )


class NoteLinkResponse(BaseSchema):
    """Response for a NoteNoteLink record."""

    id: UUID
    source_note_id: UUID
    target_note_id: UUID
    link_type: str
    block_id: str | None = None
    workspace_id: UUID
    target_note_title: str | None = None


class BacklinkResponse(BaseSchema):
    """Response for a backlink (incoming link)."""

    id: UUID
    source_note_id: UUID
    target_note_id: UUID
    link_type: str
    block_id: str | None = None
    workspace_id: UUID
    source_note_title: str | None = None


# ---------------------------------------------------------------------------
# Path parameter types
# ---------------------------------------------------------------------------

WorkspaceIdPath = Annotated[str, Path(description="Workspace ID (UUID) or slug")]
NoteIdPath = Annotated[UUID, Path(description="Note ID")]
TargetNoteIdPath = Annotated[UUID, Path(description="Target note ID")]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_uuid_or_400(value: str, entity_name: str) -> UUID:
    """Parse a string as UUID, raising 400 on malformed input."""
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {entity_name} ID format",
        ) from None


def _link_to_response(link: NoteNoteLink) -> NoteLinkResponse:
    """Convert NoteNoteLink model to outgoing link response."""
    target_title = None
    if link.target_note:
        target_title = link.target_note.title
    return NoteLinkResponse(
        id=link.id,
        source_note_id=link.source_note_id,
        target_note_id=link.target_note_id,
        link_type=link.link_type.value,
        block_id=link.block_id,
        workspace_id=link.workspace_id,
        target_note_title=target_title,
    )


def _link_to_backlink_response(link: NoteNoteLink) -> BacklinkResponse:
    """Convert NoteNoteLink model to backlink response."""
    source_title = None
    if link.source_note:
        source_title = link.source_note.title
    return BacklinkResponse(
        id=link.id,
        source_note_id=link.source_note_id,
        target_note_id=link.target_note_id,
        link_type=link.link_type.value,
        block_id=link.block_id,
        workspace_id=link.workspace_id,
        source_note_title=source_title,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{workspace_id}/notes/{note_id}/links",
    response_model=NoteLinkResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["note-note-links"],
    summary="Create a note-to-note link",
)
async def create_note_link(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    body: CreateNoteLinkRequest,
    session: SessionDep,
    current_user_id: CurrentUserId,
    link_repo: NoteNoteLinkRepositoryDep,
    note_repo: NoteRepositoryDep,
) -> NoteLinkResponse:
    """Create a note-to-note link (idempotent).

    If an identical link already exists (same source+target+block_id),
    returns the existing link with 201.
    """
    _ = current_user_id  # Auth enforced by middleware; RLS scopes queries

    ws_uuid = _parse_uuid_or_400(workspace_id, "workspace")

    # Verify source note exists in workspace
    source_note = await note_repo.get_by_id(note_id)
    if not source_note or source_note.workspace_id != ws_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source note not found in workspace",
        )

    # Verify target note exists in workspace
    target_note = await note_repo.get_by_id(body.target_note_id)
    if not target_note or target_note.workspace_id != ws_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target note not found in workspace",
        )

    # Prevent self-linking
    if note_id == body.target_note_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link a note to itself",
        )

    link_type = NoteNoteLinkType(body.link_type)

    # Check for existing link (idempotent)
    existing = await link_repo.find_existing(
        source_note_id=note_id,
        target_note_id=body.target_note_id,
        block_id=body.block_id,
        workspace_id=ws_uuid,
    )
    if existing:
        return _link_to_response(existing)

    # Create new link
    created = await link_repo.create_link(
        source_note_id=note_id,
        target_note_id=body.target_note_id,
        link_type=link_type,
        workspace_id=ws_uuid,
        block_id=body.block_id,
    )
    await session.commit()

    logger.info(
        "Created NoteNoteLink: source=%s, target=%s, type=%s",
        note_id,
        body.target_note_id,
        link_type.value,
    )

    return _link_to_response(created)


@router.delete(
    "/{workspace_id}/notes/{note_id}/links/{target_note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["note-note-links"],
    summary="Remove a note-to-note link",
)
async def delete_note_link(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    target_note_id: TargetNoteIdPath,
    session: SessionDep,
    current_user_id: CurrentUserId,
    link_repo: NoteNoteLinkRepositoryDep,
) -> None:
    """Soft-delete all links from source to target note."""
    _ = current_user_id

    ws_uuid = _parse_uuid_or_400(workspace_id, "workspace")

    count = await link_repo.delete_link(
        source_note_id=note_id,
        target_note_id=target_note_id,
        workspace_id=ws_uuid,
    )

    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No link found between these notes",
        )

    await session.commit()

    logger.info(
        "Soft-deleted %d NoteNoteLink(s): source=%s, target=%s",
        count,
        note_id,
        target_note_id,
    )


@router.get(
    "/{workspace_id}/notes/{note_id}/links",
    response_model=list[NoteLinkResponse],
    tags=["note-note-links"],
    summary="List outgoing note links",
)
async def list_note_links(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    _session: SessionDep,
    current_user_id: CurrentUserId,
    link_repo: NoteNoteLinkRepositoryDep,
) -> list[NoteLinkResponse]:
    """Get all outgoing links from a note."""
    _ = current_user_id

    ws_uuid = _parse_uuid_or_400(workspace_id, "workspace")

    links = await link_repo.find_by_source(
        source_note_id=note_id,
        workspace_id=ws_uuid,
    )

    return [_link_to_response(link) for link in links]


@router.get(
    "/{workspace_id}/notes/{note_id}/backlinks",
    response_model=list[BacklinkResponse],
    tags=["note-note-links"],
    summary="List backlinks (incoming note links)",
)
async def list_note_backlinks(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    _session: SessionDep,
    current_user_id: CurrentUserId,
    link_repo: NoteNoteLinkRepositoryDep,
) -> list[BacklinkResponse]:
    """Get all incoming links (backlinks) to a note."""
    _ = current_user_id

    ws_uuid = _parse_uuid_or_400(workspace_id, "workspace")

    links = await link_repo.find_by_target(
        target_note_id=note_id,
        workspace_id=ws_uuid,
    )

    return [_link_to_backlink_response(link) for link in links]


__all__ = ["router"]
