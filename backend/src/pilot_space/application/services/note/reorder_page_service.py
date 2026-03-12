"""ReorderPageService stub — full implementation in Plan 02.

DI slot registered in Plan 01 to avoid re-touching container.py later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )


@dataclass(frozen=True, slots=True)
class ReorderPagePayload:
    """Payload for reordering a page among its siblings.

    Attributes:
        note_id: The note to reorder.
        insert_after_id: Sibling note ID to insert after. None prepends.
        workspace_id: The workspace context.
        actor_id: The user performing the reorder.
    """

    note_id: UUID
    insert_after_id: UUID | None
    workspace_id: UUID
    actor_id: UUID


@dataclass(frozen=True, slots=True)
class ReorderPageResult:
    """Result from a page reorder operation.

    Attributes:
        note: The updated note.
        new_position: The new position value assigned.
    """

    note: Note
    new_position: int


class ReorderPageService:
    """Service for reordering a page among its siblings.

    Full implementation provided in Plan 02.
    """

    def __init__(self, session: AsyncSession, note_repository: NoteRepository) -> None:
        """Initialize ReorderPageService."""
        self._session = session
        self._note_repo = note_repository

    async def execute(self, payload: ReorderPagePayload) -> ReorderPageResult:
        """Execute the page reorder operation.

        Raises:
            NotImplementedError: Until Plan 02 provides full implementation.
        """
        raise NotImplementedError("ReorderPageService implemented in Plan 02")
