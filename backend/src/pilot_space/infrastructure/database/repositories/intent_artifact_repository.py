"""IntentArtifact repository for AI workforce platform.

Provides typed data access for intent_artifacts.
RLS enforced at DB level via join to work_intents.workspace_id.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from pilot_space.domain.intent_artifact import ArtifactType
from pilot_space.infrastructure.database.models.work_intent import IntentArtifact
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class IntentArtifactRepository(BaseRepository[IntentArtifact]):
    """Repository for IntentArtifact CRUD and intent-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_class=IntentArtifact)

    async def list_by_intent(
        self,
        intent_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[IntentArtifact]:
        """List all artifacts for a given intent.

        Args:
            intent_id: Parent WorkIntent UUID.
            include_deleted: Whether to include soft-deleted artifacts.

        Returns:
            Sequence of IntentArtifact models ordered by created_at asc.
        """
        query = select(IntentArtifact).where(IntentArtifact.intent_id == intent_id)
        if not include_deleted:
            query = query.where(IntentArtifact.is_deleted == False)  # noqa: E712
        query = query.order_by(IntentArtifact.created_at.asc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_reference(
        self,
        reference_id: UUID,
        artifact_type: ArtifactType | None = None,
        *,
        include_deleted: bool = False,
    ) -> Sequence[IntentArtifact]:
        """List artifacts pointing to a specific reference object.

        Args:
            reference_id: UUID of the referenced artifact.
            artifact_type: Optional filter by artifact type.
            include_deleted: Whether to include soft-deleted artifacts.

        Returns:
            Sequence of matching IntentArtifact models.
        """
        query = select(IntentArtifact).where(
            IntentArtifact.reference_id == reference_id,
        )
        if not include_deleted:
            query = query.where(IntentArtifact.is_deleted == False)  # noqa: E712
        if artifact_type is not None:
            query = query.where(IntentArtifact.artifact_type == artifact_type)
        query = query.order_by(IntentArtifact.created_at.asc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def bulk_create(
        self,
        artifacts: list[IntentArtifact],
    ) -> list[IntentArtifact]:
        """Create multiple artifacts in a single flush.

        Args:
            artifacts: List of IntentArtifact instances to persist.

        Returns:
            List of created artifacts with generated IDs.
        """
        self.session.add_all(artifacts)
        await self.session.flush()
        for artifact in artifacts:
            await self.session.refresh(artifact)
        return artifacts
