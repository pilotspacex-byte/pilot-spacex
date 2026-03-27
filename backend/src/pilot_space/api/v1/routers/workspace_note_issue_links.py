"""Workspace-scoped Note-Issue Link API router.

Provides REST endpoints for creating and deleting NoteIssueLink records.
Frontend caller: services/api/notes.ts (linkIssue, unlinkIssue).

Routes:
- POST   /{workspace_id}/notes/{note_id}/issues     — Link issue to note
- DELETE /{workspace_id}/notes/{note_id}/issues/{issue_id} — Unlink issue from note
- GET    /{workspace_id}/notes/{note_id}/issues     — List linked issues
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from pilot_space.api.v1.dependencies import (
    NoteIssueLinkRepositoryDep,
    NoteRepositoryDep,
)
from pilot_space.api.v1.schemas.workspace_note_issue_links import (
    LinkIssueRequest,
    NoteIssueLinkResponse,
)
from pilot_space.dependencies.auth import CurrentUserId, SessionDep
from pilot_space.infrastructure.database.models.note_issue_link import (
    NoteIssueLink,
    NoteLinkType,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Path parameter types
# ---------------------------------------------------------------------------

WorkspaceIdPath = Annotated[str, Path(description="Workspace ID (UUID) or slug")]
NoteIdPath = Annotated[UUID, Path(description="Note ID")]
IssueIdPath = Annotated[UUID, Path(description="Issue ID")]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _parse_link_type(raw: str | None) -> NoteLinkType:
    """Parse link type string to enum, defaulting to REFERENCED.

    Args:
        raw: Link type string (EXTRACTED, REFERENCED, RELATED, INLINE) or None.

    Returns:
        NoteLinkType enum value.
    """
    if not raw:
        return NoteLinkType.REFERENCED
    normalized = raw.strip().lower()
    try:
        return NoteLinkType(normalized)
    except ValueError:
        return NoteLinkType.REFERENCED


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{workspace_id}/notes/{note_id}/issues",
    response_model=NoteIssueLinkResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["note-issue-links"],
    summary="Link an issue to a note",
)
async def link_issue_to_note(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    body: LinkIssueRequest,
    session: SessionDep,
    current_user_id: CurrentUserId,
    link_repo: NoteIssueLinkRepositoryDep,
    note_repo: NoteRepositoryDep,
) -> NoteIssueLinkResponse:
    """Create a NoteIssueLink record.

    Validates that the note belongs to the workspace, then creates
    a link. If an identical link already exists (same note+issue+type),
    returns the existing link with 201.

    Args:
        workspace_id: Workspace UUID or slug.
        note_id: Note UUID.
        body: Request body with issueId, linkType, blockId.
        current_user_id: Current authenticated user.
        link_repo: NoteIssueLink repository.
        note_repo: Note repository.
        session: Database session.

    Returns:
        NoteIssueLinkResponse with 201 Created.

    Raises:
        HTTPException 404: Note not found in workspace.
    """
    _ = current_user_id  # Auth enforced by middleware; RLS scopes queries

    # Resolve workspace_id to UUID
    ws_uuid = _parse_uuid_or_404(workspace_id, "workspace")

    # Verify note exists in workspace
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != ws_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found in workspace",
        )

    link_type = _parse_link_type(body.link_type)

    # Check for existing link (idempotent)
    existing = await link_repo.find_existing(
        note_id=note_id,
        issue_id=body.issue_id,
        link_type=link_type,
        workspace_id=ws_uuid,
    )
    if existing:
        return _link_to_response(existing)

    # Create new link
    link = NoteIssueLink(
        note_id=note_id,
        issue_id=body.issue_id,
        link_type=link_type,
        block_id=body.block_id,
        workspace_id=ws_uuid,
    )
    created = await link_repo.create(link)
    await session.commit()

    logger.info(
        "Created NoteIssueLink: note=%s, issue=%s, type=%s",
        note_id,
        body.issue_id,
        link_type.value,
    )

    return _link_to_response(created)


@router.delete(
    "/{workspace_id}/notes/{note_id}/issues/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["note-issue-links"],
    summary="Unlink an issue from a note",
)
async def unlink_issue_from_note(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    issue_id: IssueIdPath,
    session: SessionDep,
    current_user_id: CurrentUserId,
    link_repo: NoteIssueLinkRepositoryDep,
) -> None:
    """Soft-delete all NoteIssueLink records between a note and issue.

    Args:
        workspace_id: Workspace UUID or slug.
        note_id: Note UUID.
        issue_id: Issue UUID.
        current_user_id: Current authenticated user.
        link_repo: NoteIssueLink repository.
        session: Database session.

    Raises:
        HTTPException 404: No links found.
    """
    _ = current_user_id

    ws_uuid = _parse_uuid_or_404(workspace_id, "workspace")

    count = await link_repo.soft_delete_by_note_and_issue(
        note_id=note_id,
        issue_id=issue_id,
        workspace_id=ws_uuid,
    )

    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No link found between this note and issue",
        )

    await session.commit()

    logger.info(
        "Soft-deleted %d NoteIssueLink(s): note=%s, issue=%s",
        count,
        note_id,
        issue_id,
    )


@router.get(
    "/{workspace_id}/notes/{note_id}/issues",
    response_model=list[NoteIssueLinkResponse],
    tags=["note-issue-links"],
    summary="List linked issues for a note",
)
async def list_note_issue_links(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    session: SessionDep,
    current_user_id: CurrentUserId,
    link_repo: NoteIssueLinkRepositoryDep,
) -> list[NoteIssueLinkResponse]:
    """Get all issue links for a note.

    Args:
        workspace_id: Workspace UUID or slug.
        note_id: Note UUID.
        current_user_id: Current authenticated user.
        link_repo: NoteIssueLink repository.

    Returns:
        List of NoteIssueLinkResponse.
    """
    _ = current_user_id

    ws_uuid = _parse_uuid_or_404(workspace_id, "workspace")

    links = await link_repo.get_by_note(
        note_id=note_id,
        workspace_id=ws_uuid,
    )

    return [_link_to_response(link) for link in links]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_uuid_or_404(value: str, entity_name: str) -> UUID:
    """Parse a string as UUID, raising 404 on failure."""
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name.capitalize()} not found",
        ) from None


def _link_to_response(link: NoteIssueLink) -> NoteIssueLinkResponse:
    """Convert NoteIssueLink model to response schema."""
    return NoteIssueLinkResponse(
        id=link.id,
        note_id=link.note_id,
        issue_id=link.issue_id,
        link_type=link.link_type.value,
        block_id=link.block_id,
        workspace_id=link.workspace_id,
    )


__all__ = ["router"]
