"""List note annotations service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note_annotation import NoteAnnotation
    from pilot_space.infrastructure.database.repositories.note_annotation_repository import (
        NoteAnnotationRepository,
    )


@dataclass(frozen=True, slots=True)
class ListAnnotationsPayload:
    """Payload for listing annotations.

    Attributes:
        note_id: The note ID to get annotations for.
    """

    note_id: UUID


@dataclass(frozen=True, slots=True)
class ListAnnotationsResult:
    """Result from annotation listing.

    Attributes:
        annotations: List of annotations.
        total: Total count.
    """

    annotations: Sequence[NoteAnnotation]
    total: int


class ListAnnotationsService:
    """Service for listing note annotations."""

    def __init__(
        self,
        session: AsyncSession,
        annotation_repository: NoteAnnotationRepository,
    ) -> None:
        """Initialize ListAnnotationsService.

        Args:
            session: The async database session.
            annotation_repository: Repository for annotation operations.
        """
        self._session = session
        self._annotation_repo = annotation_repository

    async def execute(self, payload: ListAnnotationsPayload) -> ListAnnotationsResult:
        """Execute annotation listing.

        Args:
            payload: The listing payload.

        Returns:
            ListAnnotationsResult with annotations.
        """
        annotations = await self._annotation_repo.get_by_note(payload.note_id)
        return ListAnnotationsResult(annotations=annotations, total=len(annotations))


__all__ = ["ListAnnotationsPayload", "ListAnnotationsResult", "ListAnnotationsService"]
