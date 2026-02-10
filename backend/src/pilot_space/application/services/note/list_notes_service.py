"""List notes service with filtering and pagination."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )


@dataclass(frozen=True, slots=True)
class ListNotesPayload:
    """Payload for listing notes.

    Attributes:
        workspace_id: The workspace ID to filter by.
        project_id: Optional project filter.
        is_pinned: Optional pin status filter.
        search: Optional search query.
        limit: Maximum number of notes to return.
        offset: Number of notes to skip.
    """

    workspace_id: UUID
    project_id: UUID | None = None
    is_pinned: bool | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ListNotesResult:
    """Result from note listing.

    Attributes:
        notes: List of notes.
        total: Total count (before pagination).
        has_next: Whether there are more results.
    """

    notes: Sequence[Note]
    total: int
    has_next: bool


class ListNotesService:
    """Service for listing notes with filtering.

    Handles different filtering strategies:
    - Search by title
    - Filter by project
    - Filter by pin status
    - Workspace-scoped listing
    """

    def __init__(
        self,
        session: AsyncSession,
        note_repository: NoteRepository,
    ) -> None:
        """Initialize ListNotesService.

        Args:
            session: The async database session.
            note_repository: Repository for note operations.
        """
        self._session = session
        self._note_repo = note_repository

    async def execute(self, payload: ListNotesPayload) -> ListNotesResult:
        """Execute note listing.

        Args:
            payload: The listing payload.

        Returns:
            ListNotesResult with notes and pagination info.
        """
        # Apply appropriate filtering strategy
        if payload.search:
            notes = await self._note_repo.search_by_title(
                payload.workspace_id,
                payload.search,
                project_id=payload.project_id,
                limit=payload.limit,
            )
        elif payload.project_id:
            notes = await self._note_repo.get_by_project(
                payload.project_id,
                limit=payload.limit,
            )
        elif payload.is_pinned:
            notes = await self._note_repo.get_pinned_notes(
                payload.workspace_id,
                limit=payload.limit,
            )
        else:
            notes = await self._note_repo.get_by_workspace(
                payload.workspace_id,
                limit=payload.limit,
                offset=payload.offset,
            )

        total = len(notes)
        has_next = len(notes) == payload.limit

        return ListNotesResult(
            notes=notes,
            total=total,
            has_next=has_next,
        )


__all__ = ["ListNotesPayload", "ListNotesResult", "ListNotesService"]
