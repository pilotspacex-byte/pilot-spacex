"""NoteAnnotation repository for annotation data access.

Provides specialized methods for AI annotation queries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, update

from pilot_space.infrastructure.database.models.note_annotation import (
    AnnotationStatus,
    AnnotationType,
    NoteAnnotation,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class NoteAnnotationRepository(BaseRepository[NoteAnnotation]):
    """Repository for NoteAnnotation entities.

    Extends BaseRepository with annotation-specific queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize NoteAnnotationRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, NoteAnnotation)

    async def get_by_note(
        self,
        note_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[NoteAnnotation]:
        """Get all annotations for a note.

        Args:
            note_id: The note ID.
            include_deleted: Whether to include soft-deleted annotations.

        Returns:
            List of annotations for the note.
        """
        query = select(NoteAnnotation).where(NoteAnnotation.note_id == note_id)
        if not include_deleted:
            query = query.where(NoteAnnotation.is_deleted == False)  # noqa: E712
        query = query.order_by(NoteAnnotation.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_block(
        self,
        note_id: UUID,
        block_id: str,
        *,
        include_deleted: bool = False,
    ) -> Sequence[NoteAnnotation]:
        """Get all annotations for a specific block in a note.

        Args:
            note_id: The note ID.
            block_id: The TipTap block ID.
            include_deleted: Whether to include soft-deleted annotations.

        Returns:
            List of annotations for the block.
        """
        query = select(NoteAnnotation).where(
            NoteAnnotation.note_id == note_id,
            NoteAnnotation.block_id == block_id,
        )
        if not include_deleted:
            query = query.where(NoteAnnotation.is_deleted == False)  # noqa: E712
        query = query.order_by(NoteAnnotation.confidence.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_pending(
        self,
        note_id: UUID,
        *,
        annotation_type: AnnotationType | None = None,
    ) -> Sequence[NoteAnnotation]:
        """Get all pending annotations for a note.

        Args:
            note_id: The note ID.
            annotation_type: Optional filter by annotation type.

        Returns:
            List of pending annotations.
        """
        query = select(NoteAnnotation).where(
            NoteAnnotation.note_id == note_id,
            NoteAnnotation.status == AnnotationStatus.PENDING,
            NoteAnnotation.is_deleted == False,  # noqa: E712
        )
        if annotation_type:
            query = query.where(NoteAnnotation.type == annotation_type)
        query = query.order_by(NoteAnnotation.confidence.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def batch_update_status(
        self,
        annotation_ids: list[UUID],
        new_status: AnnotationStatus,
    ) -> int:
        """Update status for multiple annotations.

        Args:
            annotation_ids: List of annotation IDs to update.
            new_status: The new status to set.

        Returns:
            Number of annotations updated.
        """
        if not annotation_ids:
            return 0

        query = (
            update(NoteAnnotation)
            .where(NoteAnnotation.id.in_(annotation_ids))
            .values(status=new_status)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount or 0  # type: ignore[return-value]

    async def get_by_type(
        self,
        note_id: UUID,
        annotation_type: AnnotationType,
        *,
        include_deleted: bool = False,
    ) -> Sequence[NoteAnnotation]:
        """Get annotations by type for a note.

        Args:
            note_id: The note ID.
            annotation_type: The type of annotations to retrieve.
            include_deleted: Whether to include soft-deleted annotations.

        Returns:
            List of annotations of the specified type.
        """
        query = select(NoteAnnotation).where(
            NoteAnnotation.note_id == note_id,
            NoteAnnotation.type == annotation_type,
        )
        if not include_deleted:
            query = query.where(NoteAnnotation.is_deleted == False)  # noqa: E712
        query = query.order_by(NoteAnnotation.confidence.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_high_confidence(
        self,
        note_id: UUID,
        *,
        min_confidence: float = 0.8,
        include_deleted: bool = False,
    ) -> Sequence[NoteAnnotation]:
        """Get high-confidence annotations for a note.

        Args:
            note_id: The note ID.
            min_confidence: Minimum confidence threshold (default 0.8).
            include_deleted: Whether to include soft-deleted annotations.

        Returns:
            List of high-confidence annotations.
        """
        query = select(NoteAnnotation).where(
            NoteAnnotation.note_id == note_id,
            NoteAnnotation.confidence >= min_confidence,
        )
        if not include_deleted:
            query = query.where(NoteAnnotation.is_deleted == False)  # noqa: E712
        query = query.order_by(NoteAnnotation.confidence.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_issue_candidates(
        self,
        note_id: UUID,
        *,
        only_pending: bool = True,
    ) -> Sequence[NoteAnnotation]:
        """Get issue candidate annotations for a note.

        These are annotations that suggest content could become an Issue.

        Args:
            note_id: The note ID.
            only_pending: Whether to only return pending candidates.

        Returns:
            List of issue candidate annotations.
        """
        query = select(NoteAnnotation).where(
            NoteAnnotation.note_id == note_id,
            NoteAnnotation.type == AnnotationType.ISSUE_CANDIDATE,
            NoteAnnotation.is_deleted == False,  # noqa: E712
        )
        if only_pending:
            query = query.where(NoteAnnotation.status == AnnotationStatus.PENDING)
        query = query.order_by(NoteAnnotation.confidence.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def dismiss_all_for_block(
        self,
        note_id: UUID,
        block_id: str,
    ) -> int:
        """Dismiss all pending annotations for a block.

        Args:
            note_id: The note ID.
            block_id: The TipTap block ID.

        Returns:
            Number of annotations dismissed.
        """
        query = (
            update(NoteAnnotation)
            .where(
                NoteAnnotation.note_id == note_id,
                NoteAnnotation.block_id == block_id,
                NoteAnnotation.status == AnnotationStatus.PENDING,
                NoteAnnotation.is_deleted == False,  # noqa: E712
            )
            .values(status=AnnotationStatus.DISMISSED)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount or 0  # type: ignore[return-value]

    async def count_by_status(
        self,
        note_id: UUID,
    ) -> dict[AnnotationStatus, int]:
        """Count annotations by status for a note.

        Args:
            note_id: The note ID.

        Returns:
            Dictionary mapping status to count.
        """
        from sqlalchemy import func

        query = (
            select(NoteAnnotation.status, func.count())
            .where(
                NoteAnnotation.note_id == note_id,
                NoteAnnotation.is_deleted == False,  # noqa: E712
            )
            .group_by(NoteAnnotation.status)
        )
        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}
