"""ListArtifactAnnotationsService — CQRS query for listing annotations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.domain.artifact_annotation import ArtifactAnnotation
    from pilot_space.infrastructure.database.repositories.artifact_annotation_repository import (
        ArtifactAnnotationRepository,
    )


@dataclass(frozen=True, slots=True)
class ListArtifactAnnotationsPayload:
    """Query payload for listing annotations.

    Attributes:
        workspace_id: Workspace scope.
        artifact_id: Artifact to query.
        slide_index: When provided, filter to a specific slide; None returns all.
    """

    workspace_id: UUID
    artifact_id: UUID
    slide_index: int | None = None


@dataclass(frozen=True, slots=True)
class ListArtifactAnnotationsResult:
    """Result from listing annotations.

    Attributes:
        annotations: Matching annotation rows.
        total: Length of annotations sequence.
    """

    annotations: Sequence[ArtifactAnnotation]
    total: int


class ListArtifactAnnotationsService:
    """Query artifact annotations with optional slide-index filter."""

    def __init__(
        self,
        session: AsyncSession,
        annotation_repo: ArtifactAnnotationRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: The async database session.
            annotation_repo: Repository for annotation queries.
        """
        self._session = session
        self._annotation_repo = annotation_repo

    async def execute(
        self, payload: ListArtifactAnnotationsPayload
    ) -> ListArtifactAnnotationsResult:
        """List annotations for an artifact.

        Args:
            payload: Query payload.

        Returns:
            ListArtifactAnnotationsResult with annotations and total.
        """
        if payload.slide_index is not None:
            annotations = await self._annotation_repo.list_by_slide(
                workspace_id=payload.workspace_id,
                artifact_id=payload.artifact_id,
                slide_index=payload.slide_index,
            )
        else:
            annotations = await self._annotation_repo.list_by_artifact(
                workspace_id=payload.workspace_id,
                artifact_id=payload.artifact_id,
            )

        return ListArtifactAnnotationsResult(
            annotations=annotations,
            total=len(annotations),
        )
