"""Repository for SkillVersion entities.

Provides workspace-scoped read/create operations for skill versions.
Versions are immutable -- no update method is provided.

Primary query patterns:
- get_by_listing: version history for a listing (newest first)
- get_latest_by_listing: current version for a listing

Source: Phase 50, P50-03
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select

from pilot_space.infrastructure.database.models.skill_version import SkillVersion
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class SkillVersionRepository(BaseRepository[SkillVersion]):
    """Repository for SkillVersion entities.

    Versions are immutable at the application level. Once created,
    a version cannot be modified -- only new versions can be published.
    The inherited BaseRepository.update() is intentionally NOT overridden.

    All write operations use flush() (no commit) -- callers own transaction
    boundaries via the session context.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SkillVersion)

    async def create(  # type: ignore[override]
        self,
        *,
        workspace_id: UUID,
        listing_id: UUID,
        version: str,
        skill_content: str,
        graph_data: dict[str, Any] | None = None,
        changelog: str | None = None,
    ) -> SkillVersion:
        """Create a new skill version.

        Args:
            workspace_id: Owning workspace UUID.
            listing_id: Parent marketplace listing UUID.
            version: Semver version string.
            skill_content: SKILL.md-format markdown content.
            graph_data: Optional graph structure snapshot.
            changelog: Human-readable description of changes.

        Returns:
            Newly created SkillVersion.
        """
        sv = SkillVersion(
            workspace_id=workspace_id,
            listing_id=listing_id,
            version=version,
            skill_content=skill_content,
            graph_data=graph_data,
            changelog=changelog,
        )
        self.session.add(sv)
        await self.session.flush()
        await self.session.refresh(sv)
        return sv

    async def get_by_listing(
        self,
        listing_id: UUID,
        *,
        limit: int = 50,
    ) -> Sequence[SkillVersion]:
        """Get all versions for a listing, newest first.

        Args:
            listing_id: The parent listing UUID.
            limit: Maximum number of rows to return.

        Returns:
            Version history for the listing, ordered by created_at descending.
        """
        query = (
            select(SkillVersion)
            .where(
                and_(
                    SkillVersion.listing_id == listing_id,
                    SkillVersion.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(SkillVersion.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_latest_by_listing(
        self,
        listing_id: UUID,
    ) -> SkillVersion | None:
        """Get the latest version for a listing.

        Args:
            listing_id: The parent listing UUID.

        Returns:
            The most recent SkillVersion, or None if no versions exist.
        """
        query = (
            select(SkillVersion)
            .where(
                and_(
                    SkillVersion.listing_id == listing_id,
                    SkillVersion.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(SkillVersion.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    # NO update method -- versions are immutable (SDM-02)


__all__ = ["SkillVersionRepository"]
