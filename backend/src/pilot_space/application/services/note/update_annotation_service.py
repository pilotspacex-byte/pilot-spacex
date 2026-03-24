"""Update annotation service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pilot_space.domain.exceptions import NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note_annotation import (
        AnnotationStatus,
        NoteAnnotation,
    )
    from pilot_space.infrastructure.database.repositories.note_annotation_repository import (
        NoteAnnotationRepository,
    )


@dataclass(frozen=True, slots=True)
class UpdateAnnotationPayload:
    """Payload for updating annotation status.

    Attributes:
        annotation_id: The annotation ID to update.
        note_id: The note the annotation must belong to (ownership check).
        status: New annotation status.
    """

    annotation_id: UUID
    note_id: UUID
    status: AnnotationStatus


@dataclass(frozen=True, slots=True)
class UpdateAnnotationResult:
    """Result from annotation update.

    Attributes:
        annotation: The updated annotation.
    """

    annotation: NoteAnnotation


class UpdateAnnotationService:
    """Service for updating annotation status.

    Handles status updates (accepted, rejected, dismissed).
    """

    def __init__(
        self,
        session: AsyncSession,
        annotation_repository: NoteAnnotationRepository,
    ) -> None:
        """Initialize UpdateAnnotationService.

        Args:
            session: The async database session.
            annotation_repository: Repository for annotation operations.
        """
        self._session = session
        self._annotation_repo = annotation_repository

    async def execute(self, payload: UpdateAnnotationPayload) -> UpdateAnnotationResult:
        """Execute annotation status update.

        Args:
            payload: The update payload.

        Returns:
            UpdateAnnotationResult with updated annotation.

        Raises:
            NotFoundError: If annotation not found.
        """
        # Get annotation
        annotation = await self._annotation_repo.get_by_id(payload.annotation_id)
        if not annotation:
            raise NotFoundError("Annotation not found")

        # Verify annotation belongs to the requested note before any mutation
        if annotation.note_id != payload.note_id:
            raise NotFoundError("Annotation not found")

        # Update status
        annotation.status = payload.status
        updated_annotation = await self._annotation_repo.update(annotation)

        await self._session.commit()

        return UpdateAnnotationResult(annotation=updated_annotation)


__all__ = ["UpdateAnnotationPayload", "UpdateAnnotationResult", "UpdateAnnotationService"]
