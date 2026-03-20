"""ArtifactRepository — data access for the artifacts table.

Handles CRUD operations for Artifact entities including:
- DB-first create (pending_upload status set before storage upload)
- Status transitions (pending_upload → ready)
- Project-scoped listing (ready only, desc order)
- Hard delete with return boolean
- Stale pending_upload cleanup for the 24h artifact cleanup job

Feature: v1.1 — Artifacts
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, delete, select, update

from pilot_space.infrastructure.database.models.artifact import Artifact

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ArtifactRepository:
    """Repository for Artifact entities.

    Artifact uses hard delete (cleanup job removes stale pending_upload records).
    Does not extend BaseRepository which assumes SoftDeleteMixin.

    Provides:
    - DB-first create for upload flow
    - Workspace + project scoped listing (status=ready only)
    - Status update for pending_upload → ready transition
    - Hard delete for explicit user-initiated deletions
    - Stale pending_upload cleanup for the 24h cleanup job
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self.session = session

    async def create(self, artifact: Artifact) -> Artifact:
        """Persist a new artifact record and return it with generated fields.

        Called BEFORE storage upload (DB-first pattern). Status is set to
        pending_upload by the caller; the cleanup job can find and remove
        stale records if the storage upload subsequently fails.

        Args:
            artifact: The Artifact instance to persist.

        Returns:
            The persisted artifact with id and server defaults populated.
        """
        self.session.add(artifact)
        await self.session.flush()
        await self.session.refresh(artifact)
        return artifact

    async def get_by_id(self, artifact_id: UUID) -> Artifact | None:
        """Fetch a single artifact by primary key.

        Args:
            artifact_id: UUID of the artifact row.

        Returns:
            Artifact if found, None otherwise.
        """
        result = await self.session.execute(select(Artifact).where(Artifact.id == artifact_id))
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        workspace_id: UUID,
        project_id: UUID,
    ) -> list[Artifact]:
        """List ready artifacts for a project, ordered by creation time descending.

        Only returns status=ready artifacts (excludes pending_upload).
        Uses the composite index ix_artifacts_workspace_project.

        Args:
            workspace_id: Workspace owning the project.
            project_id: Project to list artifacts for.

        Returns:
            List of ready Artifact rows, newest first.
        """
        result = await self.session.execute(
            select(Artifact)
            .where(
                and_(
                    Artifact.workspace_id == workspace_id,
                    Artifact.project_id == project_id,
                    Artifact.status == "ready",
                )
            )
            .order_by(Artifact.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(self, artifact_id: UUID, status: str) -> None:
        """Update the status field for an artifact.

        Used for the pending_upload → ready transition after a successful
        storage upload.

        Args:
            artifact_id: UUID of the artifact to update.
            status: New status value ("pending_upload" or "ready").
        """
        await self.session.execute(
            update(Artifact).where(Artifact.id == artifact_id).values(status=status)
        )

    async def delete(self, artifact_id: UUID) -> bool:
        """Hard-delete an artifact row by primary key.

        Args:
            artifact_id: UUID of the artifact to delete.

        Returns:
            True if a row was deleted, False if no matching row existed.
        """
        result = await self.session.execute(
            delete(Artifact).where(Artifact.id == artifact_id).returning(Artifact.id)
        )
        return result.scalar_one_or_none() is not None

    async def delete_stale_pending(self, older_than: datetime) -> list[Artifact]:
        """Fetch and hard-delete pending_upload records older than the cutoff.

        Used by the artifact_cleanup background job to remove stale upload
        attempts and their associated storage objects.

        Fetches the stale records first (to get storage_key values for storage
        cleanup), then bulk-deletes them from the DB.

        Args:
            older_than: Cutoff datetime; records with created_at before this
                value are considered stale.

        Returns:
            List of stale Artifact records that were deleted (for storage cleanup).
        """
        result = await self.session.execute(
            select(Artifact).where(
                and_(
                    Artifact.status == "pending_upload",
                    Artifact.created_at < older_than,
                )
            )
        )
        stale = list(result.scalars().all())
        if stale:
            ids = [a.id for a in stale]
            await self.session.execute(delete(Artifact).where(Artifact.id.in_(ids)))
        return stale


__all__ = ["ArtifactRepository"]
