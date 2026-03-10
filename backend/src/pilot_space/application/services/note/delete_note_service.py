"""Delete note service with audit log tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.audit_log_repository import (
        AuditLogRepository,
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
    """Service for deleting notes (soft delete) with audit logging."""

    def __init__(
        self,
        session: AsyncSession,
        note_repository: NoteRepository,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        """Initialize DeleteNoteService.

        Args:
            session: The async database session.
            note_repository: Repository for note operations.
            audit_log_repository: Optional audit log repository for compliance writes.
        """
        self._session = session
        self._note_repo = note_repository
        self._audit_repo = audit_log_repository

    async def execute(self, payload: DeleteNotePayload) -> DeleteNoteResult:
        """Execute note deletion.

        Args:
            payload: The deletion payload.

        Returns:
            DeleteNoteResult with deletion status.

        Raises:
            ValueError: If note not found.
        """
        import logging

        logger = logging.getLogger(__name__)

        # Get note
        note = await self._note_repo.get_by_id(payload.note_id)
        if not note:
            raise ValueError("Note not found")

        # Soft delete
        await self._note_repo.delete(note)

        # Write audit log entry (non-fatal)
        if self._audit_repo is not None:
            try:
                from pilot_space.infrastructure.database.models.audit_log import ActorType

                await self._audit_repo.create(
                    workspace_id=note.workspace_id,
                    actor_id=payload.actor_id,
                    actor_type=ActorType.USER,
                    action="note.delete",
                    resource_type="note",
                    resource_id=note.id,
                    payload={"before": {"title": note.title}, "after": {}},
                    ip_address=None,
                )
            except Exception as exc:
                logger.warning("DeleteNoteService: failed to write audit log: %s", exc)

        await self._session.commit()

        return DeleteNoteResult(note_id=payload.note_id, success=True)


__all__ = ["DeleteNotePayload", "DeleteNoteResult", "DeleteNoteService"]
