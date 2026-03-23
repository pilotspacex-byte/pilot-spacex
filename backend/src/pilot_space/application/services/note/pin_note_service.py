"""Pin/unpin note service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pilot_space.domain.exceptions import NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )


@dataclass(frozen=True, slots=True)
class PinNotePayload:
    """Payload for pinning/unpinning a note.

    Attributes:
        note_id: The note ID to pin/unpin.
        is_pinned: True to pin, False to unpin.
    """

    note_id: UUID
    is_pinned: bool


@dataclass(frozen=True, slots=True)
class PinNoteResult:
    """Result from pin operation.

    Attributes:
        note: The updated note.
        is_pinned: Current pin status.
    """

    note: Note
    is_pinned: bool


class PinNoteService:
    """Service for pinning/unpinning notes.

    Handles toggling pin status for quick access.
    """

    def __init__(
        self,
        session: AsyncSession,
        note_repository: NoteRepository,
    ) -> None:
        """Initialize PinNoteService.

        Args:
            session: The async database session.
            note_repository: Repository for note operations.
        """
        self._session = session
        self._note_repo = note_repository

    async def execute(self, payload: PinNotePayload) -> PinNoteResult:
        """Execute pin/unpin operation.

        Args:
            payload: The pin payload.

        Returns:
            PinNoteResult with updated note.

        Raises:
            ValueError: If note not found.
        """
        # Get note
        note = await self._note_repo.get_by_id(payload.note_id)
        if not note:
            raise NotFoundError("Note not found")

        # Update pin status
        note.is_pinned = payload.is_pinned
        updated_note = await self._note_repo.update(note)

        await self._session.commit()

        return PinNoteResult(note=updated_note, is_pinned=updated_note.is_pinned)


__all__ = ["PinNotePayload", "PinNoteResult", "PinNoteService"]
