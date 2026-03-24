"""ArtifactAnnotationRepository — data access for artifact annotations.

Provides queries scoped by artifact and optional slide index.
Hard delete: remove() permanently deletes the row.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from pilot_space.domain.artifact_annotation import ArtifactAnnotation
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class ArtifactAnnotationRepository(BaseRepository[ArtifactAnnotation]):
    """Repository for ArtifactAnnotation entities.

    Extends BaseRepository with artifact-specific queries.
    All public list methods exclude soft-deleted rows (is_deleted=False)
    for consistency, although the service layer always calls hard delete.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize ArtifactAnnotationRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, ArtifactAnnotation)

    async def list_by_artifact(
        self,
        workspace_id: UUID,
        artifact_id: UUID,
    ) -> Sequence[ArtifactAnnotation]:
        """Return all annotations for an artifact (all slides), newest first.

        Args:
            workspace_id: Workspace scope for RLS enforcement.
            artifact_id: The artifact to query.

        Returns:
            Sequence of ArtifactAnnotation ordered by created_at desc.
        """
        query = (
            select(ArtifactAnnotation)
            .where(
                ArtifactAnnotation.workspace_id == workspace_id,
                ArtifactAnnotation.artifact_id == artifact_id,
                ArtifactAnnotation.is_deleted == False,  # noqa: E712
            )
            .order_by(ArtifactAnnotation.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_slide(
        self,
        workspace_id: UUID,
        artifact_id: UUID,
        slide_index: int,
    ) -> Sequence[ArtifactAnnotation]:
        """Return annotations for a specific slide, newest first.

        Args:
            workspace_id: Workspace scope for RLS enforcement.
            artifact_id: The artifact to query.
            slide_index: Zero-based slide/page index.

        Returns:
            Sequence of ArtifactAnnotation for the given slide.
        """
        query = (
            select(ArtifactAnnotation)
            .where(
                ArtifactAnnotation.workspace_id == workspace_id,
                ArtifactAnnotation.artifact_id == artifact_id,
                ArtifactAnnotation.slide_index == slide_index,
                ArtifactAnnotation.is_deleted == False,  # noqa: E712
            )
            .order_by(ArtifactAnnotation.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_for_artifact(
        self,
        workspace_id: UUID,
        artifact_id: UUID,
        annotation_id: UUID,
    ) -> ArtifactAnnotation | None:
        """Fetch a single annotation with workspace + artifact ownership check.

        Args:
            workspace_id: Workspace scope.
            artifact_id: Artifact scope.
            annotation_id: The annotation primary key.

        Returns:
            ArtifactAnnotation if found and not deleted, else None.
        """
        query = select(ArtifactAnnotation).where(
            ArtifactAnnotation.id == annotation_id,
            ArtifactAnnotation.workspace_id == workspace_id,
            ArtifactAnnotation.artifact_id == artifact_id,
            ArtifactAnnotation.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def remove(self, annotation: ArtifactAnnotation) -> None:
        """Hard-delete an annotation permanently.

        Args:
            annotation: The annotation to delete.
        """
        await self.session.delete(annotation)
        await self.session.flush()


__all__ = ["ArtifactAnnotationRepository"]
