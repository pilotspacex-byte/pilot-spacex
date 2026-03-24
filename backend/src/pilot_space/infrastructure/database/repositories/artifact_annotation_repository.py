"""ArtifactAnnotationRepository — data access for the artifact_annotations table.

Handles CRUD operations for ArtifactAnnotation entities including:
- Create new annotation for a slide
- List annotations by artifact + slide index (ordered by created_at asc)
- Get single annotation by id
- Update annotation content (author-only check enforced at router layer)
- Hard delete with boolean return

Feature: v1.2 — PPTX Annotations
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, func, select, update

from pilot_space.infrastructure.database.models.artifact_annotation import ArtifactAnnotation

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ArtifactAnnotationRepository:
    """Repository for ArtifactAnnotation entities.

    Uses hard delete. Author-only enforcement for PUT/DELETE is handled
    at the router layer; RLS enforces workspace isolation at the DB layer.

    Provides:
    - Create and return annotation with generated fields
    - Slide-scoped listing ordered by created_at ascending
    - Single annotation lookup by primary key
    - Content update by annotation id
    - Hard delete returning bool
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self.session = session

    async def create(self, annotation: ArtifactAnnotation) -> ArtifactAnnotation:
        """Persist a new annotation and return it with generated fields.

        Args:
            annotation: The ArtifactAnnotation instance to persist.

        Returns:
            The persisted annotation with id and server defaults populated.
        """
        self.session.add(annotation)
        await self.session.flush()
        await self.session.refresh(annotation)
        return annotation

    async def list_by_slide(
        self,
        artifact_id: UUID,
        slide_index: int,
    ) -> list[ArtifactAnnotation]:
        """List annotations for a specific slide, ordered by creation time ascending.

        Uses the composite index ix_artifact_annotations_artifact_slide.

        Args:
            artifact_id: Artifact to list annotations for.
            slide_index: Zero-based slide index to filter by.

        Returns:
            List of ArtifactAnnotation rows, oldest first.
        """
        result = await self.session.execute(
            select(ArtifactAnnotation)
            .where(
                ArtifactAnnotation.artifact_id == artifact_id,
                ArtifactAnnotation.slide_index == slide_index,
            )
            .order_by(ArtifactAnnotation.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, annotation_id: UUID) -> ArtifactAnnotation | None:
        """Fetch a single annotation by primary key.

        Args:
            annotation_id: UUID of the annotation row.

        Returns:
            ArtifactAnnotation if found, None otherwise.
        """
        result = await self.session.execute(
            select(ArtifactAnnotation).where(ArtifactAnnotation.id == annotation_id)
        )
        return result.scalar_one_or_none()

    async def update_content(self, annotation_id: UUID, content: str) -> None:
        """Update the content field for an annotation.

        Args:
            annotation_id: UUID of the annotation to update.
            content: New content value.
        """
        await self.session.execute(
            update(ArtifactAnnotation)
            .where(ArtifactAnnotation.id == annotation_id)
            .values(content=content, updated_at=func.now())
        )
        # Expire any cached ORM instance so the next get_by_id fetches fresh data
        # (Core-level update bypasses the ORM identity map)
        self.session.expire_all()

    async def delete(self, annotation_id: UUID) -> bool:
        """Hard-delete an annotation row by primary key.

        Args:
            annotation_id: UUID of the annotation to delete.

        Returns:
            True if a row was deleted, False if no matching row existed.
        """
        result = await self.session.execute(
            delete(ArtifactAnnotation)
            .where(ArtifactAnnotation.id == annotation_id)
            .returning(ArtifactAnnotation.id)
        )
        return result.scalar_one_or_none() is not None


__all__ = ["ArtifactAnnotationRepository"]
