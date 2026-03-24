"""CreateArtifactAnnotationService — CQRS command for annotation creation.

Validates artifact ownership and persists a new annotation row.
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
    from pilot_space.infrastructure.database.repositories.artifact_repository import (
        ArtifactRepository,
    )


@dataclass(frozen=True, slots=True)
class CreateArtifactAnnotationPayload:
    """Payload for creating an artifact annotation.

    Attributes:
        workspace_id: Workspace scope.
        artifact_id: Artifact to annotate.
        project_id: Project owning the artifact (for ownership check).
        user_id: Authenticated user creating the annotation.
        slide_index: Zero-based slide/page index.
        content: Annotation text (already validated by schema).
    """

    workspace_id: UUID
    artifact_id: UUID
    project_id: UUID
    user_id: UUID
    slide_index: int
    content: str


class CreateArtifactAnnotationService:
    """Create a user annotation on a project artifact.

    Raises ValueError for ownership violations so the router can map
    them to the appropriate HTTP status codes.
    """

    def __init__(
        self,
        session: AsyncSession,
        artifact_repo: ArtifactRepository,
        annotation_repo: ArtifactAnnotationRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: The async database session.
            artifact_repo: Repository for artifact ownership checks.
            annotation_repo: Repository for annotation persistence.
        """
        self._session = session
        self._artifact_repo = artifact_repo
        self._annotation_repo = annotation_repo

    async def execute(self, payload: CreateArtifactAnnotationPayload) -> ArtifactAnnotation:
        """Create and persist an annotation.

        Args:
            payload: Creation payload with validated fields.

        Returns:
            The created ArtifactAnnotation with generated ID and timestamps.

        Raises:
            ValueError: If the artifact is not found or does not belong to
                the given workspace/project.
        """
        from pilot_space.domain.artifact_annotation import ArtifactAnnotation

        artifact = await self._artifact_repo.get_by_id(payload.artifact_id)
        if (
            artifact is None
            or artifact.workspace_id != payload.workspace_id
            or artifact.project_id != payload.project_id
        ):
            msg = "Artifact not found"
            raise ValueError(msg)

        annotation = ArtifactAnnotation(
            workspace_id=payload.workspace_id,
            artifact_id=payload.artifact_id,
            user_id=payload.user_id,
            slide_index=payload.slide_index,
            content=payload.content.strip(),
        )
        return await self._annotation_repo.create(annotation)
