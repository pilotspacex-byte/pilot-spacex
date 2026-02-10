"""Delete note service with activity tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.activity_repository import (
        ActivityRepository,
    )
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )


@dataclass(frozen=True, slots=True)
class DeleteNotePayload:
    """Payload for deleting a note.

    Attributes:
        note_id: The note ID to delete.
        actor_id: The user ID performing the deletion.
    """

    note_id: UUID
    actor_id: UUID


@dataclass(frozen=True, slots=True)
class DeleteNoteResult:
    """Result from note deletion.

    Attributes:
        note_id: ID of the deleted note.
        success: Whether the deletion was successful.
    """

    note_id: UUID
    success: bool


class DeleteNoteService:
    """Service for deleting notes (soft delete).

    Handles soft deletion of notes and tracks activity.
    """

    def __init__(
        self,
        session: AsyncSession,
        note_repository: NoteRepository,
        activity_repository: ActivityRepository,
    ) -> None:
        """Initialize DeleteNoteService.

        Args:
            session: The async database session.
            note_repository: Repository for note operations.
            activity_repository: Repository for activity tracking.
        """
        self._session = session
        self._note_repo = note_repository
        self._activity_repo = activity_repository

    async def execute(self, payload: DeleteNotePayload) -> DeleteNoteResult:
        """Execute note deletion.

        Args:
            payload: The deletion payload.

        Returns:
            DeleteNoteResult with deletion status.

        Raises:
            ValueError: If note not found.
        """
        # Get note
        note = await self._note_repo.get_by_id(payload.note_id)
        if not note:
            raise ValueError("Note not found")

        # Soft delete
        await self._note_repo.delete(note)

        # Track deletion activity
        from pilot_space.infrastructure.database.models.activity import Activity, ActivityType

        activity = Activity(
            workspace_id=note.workspace_id,
            actor_id=payload.actor_id,
            verb=ActivityType.DELETED,
            object_type="note",
            object_id=note.id,
            metadata={"title": note.title},
        )
        await self._activity_repo.create(activity)

        await self._session.commit()

        return DeleteNoteResult(note_id=payload.note_id, success=True)


__all__ = ["DeleteNotePayload", "DeleteNoteResult", "DeleteNoteService"]
