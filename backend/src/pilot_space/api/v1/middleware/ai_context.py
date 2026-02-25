"""AI context extraction middleware.

Extracts AI-related context from requests (note_id, issue_id, workspace_id, etc.)
and attaches it to request.state for use by AI agents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, Request, status

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models import Issue, Note


async def extract_ai_context(
    request: Request,
    session: AsyncSession,  # type: ignore[type-arg]
    note_id: UUID | None = None,
    issue_id: UUID | None = None,
    workspace_id: UUID | None = None,
    selected_text: str | None = None,
) -> dict[str, object]:
    """Extract AI context from request parameters.

    Loads full context objects (Note, Issue) if IDs are provided and
    attaches them to request.state for use by AI agents.

    Args:
        request: FastAPI request.
        session: Database session.
        note_id: Optional note ID to load.
        issue_id: Optional issue ID to load.
        workspace_id: Optional workspace ID (falls back to request.state).
        selected_text: Optional selected text from editor.

    Returns:
        Dictionary with AI context objects.

    Raises:
        HTTPException: If referenced entities not found.
    """
    context: dict[str, object] = {}

    # Get workspace ID from request state if not provided
    if workspace_id is None:
        workspace_id = getattr(request.state, "workspace_id", None)

    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace context required for AI operations",
        )

    context["workspace_id"] = workspace_id

    # Load note if note_id provided
    if note_id is not None:
        note = await _load_note(session, note_id, workspace_id)
        if note is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note not found: {note_id}",
            )
        context["note"] = note
        context["note_id"] = note_id

    # Load issue if issue_id provided
    if issue_id is not None:
        issue = await _load_issue(session, issue_id, workspace_id)
        if issue is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Issue not found: {issue_id}",
            )
        context["issue"] = issue
        context["issue_id"] = issue_id

    # Include selected text if provided
    if selected_text is not None:
        context["selected_text"] = selected_text

    # Attach to request.state for downstream handlers
    request.state.ai_context = context

    return context


async def _load_note(
    session: AsyncSession,  # type: ignore[type-arg]
    note_id: UUID,
    workspace_id: UUID,
) -> Note | None:  # type: ignore[name-defined]
    """Load note from database.

    Args:
        session: Database session.
        note_id: Note UUID.
        workspace_id: Workspace UUID for RLS.

    Returns:
        Note object or None if not found.
    """
    from pilot_space.infrastructure.database.repositories import NoteRepository

    repo = NoteRepository(session)
    # RLS will enforce workspace_id access
    return await repo.get_by_id(note_id)


async def _load_issue(
    session: AsyncSession,  # type: ignore[type-arg]
    issue_id: UUID,
    workspace_id: UUID,
) -> Issue | None:  # type: ignore[name-defined]
    """Load issue from database.

    Args:
        session: Database session.
        issue_id: Issue UUID.
        workspace_id: Workspace UUID for RLS.

    Returns:
        Issue object or None if not found.
    """
    from pilot_space.infrastructure.database.repositories import IssueRepository

    repo = IssueRepository(session)
    # Load with relations (project, state) so context enrichment can access
    # issue.identifier and issue.state.name without triggering lazy loads.
    return await repo.get_by_id_with_relations(issue_id)
