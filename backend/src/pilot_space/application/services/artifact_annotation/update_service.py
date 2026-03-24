"""UpdateArtifactAnnotationService — CQRS command for annotation updates.

Only the content field is mutable after creation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.domain.artifact_annotation import ArtifactAnnotation
    from pilot_space.infrastructure.database.repositories.artifact_annotation_repository import (
        ArtifactAnnotationRepository,
    )


@dataclass(frozen=True, slots=True)
class UpdateArtifactAnnotationPayload:
    """Payload for updating an artifact annotation.

    Attributes:
        workspace_id: Workspace scope.
        artifact_id: Artifact scope.
        annotation_id: Annotation to update.
        content: New annotation text (already validated by schema).
    """

    workspace_id: UUID
    artifact_id: UUID
    annotation_id: UUID
    content: str


class UpdateArtifactAnnotationService:
    """Update the content of an existing artifact annotation."""

    def __init__(
        self,
        session: AsyncSession,
        annotation_repo: ArtifactAnnotationRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: The async database session.
            annotation_repo: Repository for annotation persistence.
        """
        self._session = session
        self._annotation_repo = annotation_repo

    async def execute(self, payload: UpdateArtifactAnnotationPayload) -> ArtifactAnnotation:
        """Update annotation content.

        Args:
            payload: Update payload with validated fields.

        Returns:
            The updated ArtifactAnnotation.

        Raises:
            ValueError: If the annotation is not found or does not belong to
                the given workspace/artifact.
        """
        annotation = await self._annotation_repo.get_for_artifact(
            workspace_id=payload.workspace_id,
            artifact_id=payload.artifact_id,
            annotation_id=payload.annotation_id,
        )
        if annotation is None:
            msg = "Annotation not found"
            raise ValueError(msg)

        annotation.content = payload.content.strip()
        return await self._annotation_repo.update(annotation)
