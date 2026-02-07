"""Digest repository for workspace digest and dismissal data access.

Provides methods for:
- Fetching the latest workspace digest
- Saving new digests
- Managing per-user suggestion dismissals
- Checking recent digest existence (cooldown guard)

References:
- specs/012-homepage-note/spec.md Digest Endpoints
- US-19: Homepage Hub feature
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, delete, desc, func, select

from pilot_space.infrastructure.database.models.digest_dismissal import DigestDismissal
from pilot_space.infrastructure.database.models.workspace_digest import WorkspaceDigest
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class DigestRepository(BaseRepository[WorkspaceDigest]):
    """Repository for WorkspaceDigest entities.

    Extends BaseRepository with digest-specific queries including
    latest-digest lookup and cooldown checking.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize DigestRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, WorkspaceDigest)

    async def get_latest_digest(
        self,
        workspace_id: UUID,
    ) -> WorkspaceDigest | None:
        """Get the most recent digest for a workspace.

        Args:
            workspace_id: Workspace to query.

        Returns:
            Latest WorkspaceDigest or None if no digest exists.
        """
        query = (
            select(WorkspaceDigest)
            .where(
                WorkspaceDigest.workspace_id == workspace_id,
                WorkspaceDigest.is_deleted == False,  # noqa: E712
            )
            .order_by(desc(WorkspaceDigest.generated_at))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def save_digest(self, digest: WorkspaceDigest) -> WorkspaceDigest:
        """Persist a new workspace digest.

        Args:
            digest: The WorkspaceDigest entity to save.

        Returns:
            The saved digest with generated ID.
        """
        return await self.create(digest)

    async def check_recent_digest_exists(
        self,
        workspace_id: UUID,
        *,
        since: datetime,
    ) -> bool:
        """Check if a digest was generated recently (cooldown guard).

        Used to prevent excessive on-demand digest generation.

        Args:
            workspace_id: Workspace to check.
            since: Only consider digests generated at or after this time.

        Returns:
            True if a recent digest exists, False otherwise.
        """
        query = (
            select(func.count())
            .select_from(WorkspaceDigest)
            .where(
                WorkspaceDigest.workspace_id == workspace_id,
                WorkspaceDigest.generated_at >= since,
                WorkspaceDigest.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return (result.scalar() or 0) > 0


class DismissalRepository(BaseRepository[DigestDismissal]):
    """Repository for DigestDismissal entities.

    Manages per-user suggestion dismissals with workspace-scoped queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize DismissalRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, DigestDismissal)

    async def get_user_dismissals(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Sequence[DigestDismissal]:
        """Get all active dismissals for a user in a workspace.

        Args:
            workspace_id: Workspace to query.
            user_id: User whose dismissals to fetch.

        Returns:
            Sequence of DigestDismissal entities.
        """
        query = (
            select(DigestDismissal)
            .where(
                DigestDismissal.workspace_id == workspace_id,
                DigestDismissal.user_id == user_id,
                DigestDismissal.is_deleted == False,  # noqa: E712
            )
            .order_by(desc(DigestDismissal.dismissed_at))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_dismissed_entity_ids(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> set[tuple[str, str]]:
        """Get set of (entity_id, category) pairs dismissed by user.

        Optimised query returning only the identifiers needed for
        filtering suggestions in the service layer.

        Args:
            workspace_id: Workspace to query.
            user_id: User whose dismissals to check.

        Returns:
            Set of (entity_id_hex, category) tuples.
        """
        query = select(
            DigestDismissal.entity_id,
            DigestDismissal.suggestion_category,
        ).where(
            DigestDismissal.workspace_id == workspace_id,
            DigestDismissal.user_id == user_id,
            DigestDismissal.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(query)
        return {(str(r.entity_id), r.suggestion_category) for r in result.all()}

    async def add_dismissal(
        self,
        dismissal: DigestDismissal,
    ) -> DigestDismissal:
        """Persist a new dismissal.

        Args:
            dismissal: The DigestDismissal entity to save.

        Returns:
            The saved dismissal with generated ID.
        """
        return await self.create(dismissal)

    async def remove_dismissal(
        self,
        workspace_id: UUID,
        user_id: UUID,
        entity_id: UUID,
        category: str,
    ) -> None:
        """Hard-delete a specific dismissal (un-dismiss).

        Args:
            workspace_id: Workspace scope.
            user_id: User who owns the dismissal.
            entity_id: Entity that was dismissed.
            category: Suggestion category to match.
        """
        stmt = delete(DigestDismissal).where(
            and_(
                DigestDismissal.workspace_id == workspace_id,
                DigestDismissal.user_id == user_id,
                DigestDismissal.entity_id == entity_id,
                DigestDismissal.suggestion_category == category,
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
