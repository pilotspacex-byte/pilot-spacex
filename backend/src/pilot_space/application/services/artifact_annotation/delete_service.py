"""DeleteArtifactAnnotationService — CQRS command for hard-deleting annotations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.artifact_annotation_repository import (
        ArtifactAnnotationRepository,
    )


class DeleteArtifactAnnotationService:
    """Hard-delete an artifact annotation.

    Raises ValueError if the annotation is not found so the router can
    return 404 rather than silently succeeding.
    """

    def __init__(
        self,
        session: AsyncSession,
        annotation_repo: ArtifactAnnotationRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: The async database session.
            annotation_repo: Repository for annotation deletion.
        """
        self._session = session
        self._annotation_repo = annotation_repo

    async def execute(
        self,
        workspace_id: UUID,
        artifact_id: UUID,
        annotation_id: UUID,
    ) -> None:
        """Hard-delete the annotation.

        Args:
            workspace_id: Workspace scope (prevents cross-tenant access).
            artifact_id: Artifact scope.
            annotation_id: Annotation to delete.

        Raises:
            ValueError: If the annotation is not found.
        """
        annotation = await self._annotation_repo.get_for_artifact(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            annotation_id=annotation_id,
        )
        if annotation is None:
            msg = "Annotation not found"
            raise ValueError(msg)

        await self._annotation_repo.remove(annotation)
