"""Repository for SkillMarketplaceListing entities.

Provides workspace-scoped CRUD operations for marketplace listings.
Primary query patterns:
- get_by_category: browse by category (ordered by download_count)
- get_by_workspace: workspace admin list (non-deleted only)
- search: text search across name and description

Source: Phase 50, P50-03
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, or_, select

from pilot_space.infrastructure.database.models.skill_marketplace_listing import (
    SkillMarketplaceListing,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class SkillMarketplaceListingRepository(BaseRepository[SkillMarketplaceListing]):
    """Repository for SkillMarketplaceListing entities.

    All write operations use flush() (no commit) -- callers own transaction
    boundaries via the session context.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SkillMarketplaceListing)

    async def create(  # type: ignore[override]
        self,
        *,
        workspace_id: UUID,
        name: str,
        description: str,
        author: str,
        category: str,
        version: str,
        long_description: str | None = None,
        icon: str = "Wand2",
        tags: list[str] | None = None,
        screenshots: list[str] | None = None,
        graph_data: dict[str, Any] | None = None,
        published_by: UUID | None = None,
    ) -> SkillMarketplaceListing:
        """Create a new marketplace listing.

        Args:
            workspace_id: Owning workspace UUID.
            name: Listing display name.
            description: Brief description for marketplace cards.
            author: Author name or organization.
            category: Skill category for filtering.
            version: Semver version string.
            long_description: Extended description for detail pages.
            icon: Frontend icon identifier.
            tags: List of string tags for search.
            screenshots: List of screenshot URLs.
            graph_data: Optional graph structure for visual preview.
            published_by: User UUID who published this listing.

        Returns:
            Newly created SkillMarketplaceListing.
        """
        listing = SkillMarketplaceListing(
            workspace_id=workspace_id,
            name=name,
            description=description,
            author=author,
            category=category,
            version=version,
            long_description=long_description,
            icon=icon,
            tags=tags or [],
            screenshots=screenshots,
            graph_data=graph_data,
            published_by=published_by,
        )
        self.session.add(listing)
        await self.session.flush()
        await self.session.refresh(listing)
        return listing

    async def get_by_category(
        self,
        category: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[SkillMarketplaceListing]:
        """Get listings by category, ordered by popularity.

        Args:
            category: Category string to filter by.
            limit: Maximum number of rows to return.
            offset: Number of rows to skip for pagination.

        Returns:
            Listings in the given category, ordered by download_count descending.
        """
        query = (
            select(SkillMarketplaceListing)
            .where(
                and_(
                    SkillMarketplaceListing.category == category,
                    SkillMarketplaceListing.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(SkillMarketplaceListing.download_count.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[SkillMarketplaceListing]:
        """Get all non-deleted listings for a workspace.

        Args:
            workspace_id: The workspace UUID.
            limit: Maximum number of rows to return.
            offset: Number of rows to skip for pagination.

        Returns:
            All non-deleted listings for the workspace, newest first.
        """
        query = (
            select(SkillMarketplaceListing)
            .where(
                and_(
                    SkillMarketplaceListing.workspace_id == workspace_id,
                    SkillMarketplaceListing.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(SkillMarketplaceListing.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def search(  # type: ignore[override]
        self,
        search_term: str,
        search_columns: list[str] | None = None,
        *,
        include_deleted: bool = False,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[SkillMarketplaceListing]:
        """Search listings by name or description text.

        Overrides BaseRepository.search with marketplace-specific filtering.

        Args:
            search_term: Text to search for (ILIKE match).
            search_columns: Ignored - always searches name and description.
            include_deleted: Whether to include soft-deleted listings.
            category: Optional category filter.
            limit: Maximum number of rows to return.
            offset: Number of rows to skip for pagination.

        Returns:
            Matching listings ordered by download_count descending.
        """
        _ = search_columns  # Always searches name + description
        pattern = f"%{search_term}%"
        conditions = [
            or_(
                SkillMarketplaceListing.name.ilike(pattern),
                SkillMarketplaceListing.description.ilike(pattern),
            ),
        ]
        if not include_deleted:
            conditions.append(
                SkillMarketplaceListing.is_deleted == False,  # noqa: E712
            )
        if category:
            conditions.append(SkillMarketplaceListing.category == category)
        query = (
            select(SkillMarketplaceListing)
            .where(and_(*conditions))
            .order_by(SkillMarketplaceListing.download_count.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def increment_download_count(
        self,
        listing_id: UUID,
    ) -> SkillMarketplaceListing | None:
        """Increment the download count for a listing.

        Args:
            listing_id: The listing UUID.

        Returns:
            Updated listing, or None if not found.
        """
        listing = await self.get_by_id(listing_id)
        if listing is None:
            return None
        listing.download_count += 1
        await self.session.flush()
        await self.session.refresh(listing)
        return listing

    async def update_avg_rating(
        self,
        listing_id: UUID,
        new_avg: float,
    ) -> SkillMarketplaceListing | None:
        """Update the average rating for a listing.

        Args:
            listing_id: The listing UUID.
            new_avg: New average rating value.

        Returns:
            Updated listing, or None if not found.
        """
        listing = await self.get_by_id(listing_id)
        if listing is None:
            return None
        listing.avg_rating = new_avg
        await self.session.flush()
        await self.session.refresh(listing)
        return listing


__all__ = ["SkillMarketplaceListingRepository"]
