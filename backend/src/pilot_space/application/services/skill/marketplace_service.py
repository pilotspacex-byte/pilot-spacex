"""Marketplace service for publishing, searching, and versioning skills.

Handles marketplace CRUD operations: publish listings from skill templates,
search/filter listings, and manage semver-ordered version history.

Source: Phase 054, P54-01
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from pilot_space.domain.exceptions import ConflictError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.repositories.skill_marketplace_listing_repository import (
    SkillMarketplaceListingRepository,
)
from pilot_space.infrastructure.database.repositories.skill_template_repository import (
    SkillTemplateRepository,
)
from pilot_space.infrastructure.database.repositories.skill_version_repository import (
    SkillVersionRepository,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.skill_marketplace_listing import (
        SkillMarketplaceListing,
    )
    from pilot_space.infrastructure.database.models.skill_version import SkillVersion

logger = get_logger(__name__)


@dataclass
class PublishListingPayload:
    """Input for publishing a skill template to the marketplace."""

    workspace_id: UUID
    skill_template_id: UUID
    user_id: UUID
    name: str
    description: str
    author: str
    category: str
    version: str
    long_description: str | None = None
    icon: str = "Wand2"
    tags: list[str] = field(default_factory=list)
    screenshots: list[str] | None = None
    graph_data: dict[str, Any] | None = None


@dataclass
class CreateVersionPayload:
    """Input for creating a new version of a marketplace listing."""

    workspace_id: UUID
    listing_id: UUID
    version: str
    skill_content: str
    changelog: str | None = None
    graph_data: dict[str, Any] | None = None


@dataclass
class SearchPayload:
    """Input for searching marketplace listings."""

    query: str | None = None
    category: str | None = None
    min_rating: float | None = None
    sort: str = "popular"
    limit: int = 20
    offset: int = 0


@dataclass
class SearchResult:
    """Paginated search result."""

    items: list[SkillMarketplaceListing]
    total: int
    has_next: bool


def _parse_semver(version: str) -> tuple[int, int, int]:
    """Parse a semver string into a comparable tuple.

    Args:
        version: Semver string in X.Y.Z format.

    Returns:
        Tuple of (major, minor, patch) integers.
    """
    parts = version.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


class MarketplaceService:
    """Service for marketplace listing and version operations.

    Constructs repositories internally from the session (same pattern
    as other skill services that don't use DI-injected repos).

    Args:
        session: Request-scoped async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._listing_repo = SkillMarketplaceListingRepository(session)
        self._version_repo = SkillVersionRepository(session)
        self._template_repo = SkillTemplateRepository(session)

    async def publish_listing(
        self, payload: PublishListingPayload
    ) -> SkillMarketplaceListing:
        """Publish a skill template as a marketplace listing.

        Creates the listing and an initial version from the template's
        skill_content.

        Args:
            payload: Publish parameters including template ID.

        Returns:
            Newly created marketplace listing.

        Raises:
            NotFoundError: If the skill template does not exist.
            ConflictError: If a listing with the same name+author already exists.
        """
        # Look up the source template
        template = await self._template_repo.get_by_id(payload.skill_template_id)
        if template is None:
            raise NotFoundError("Skill template not found")

        # Create the listing
        try:
            listing = await self._listing_repo.create(
                workspace_id=payload.workspace_id,
                name=payload.name,
                description=payload.description,
                author=payload.author,
                category=payload.category,
                version=payload.version,
                long_description=payload.long_description,
                icon=payload.icon,
                tags=payload.tags,
                screenshots=payload.screenshots,
                graph_data=payload.graph_data,
                published_by=payload.user_id,
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Listing with name '{payload.name}' by '{payload.author}' already exists"
            ) from exc

        # Create the initial version from the template's content
        await self._version_repo.create(
            workspace_id=payload.workspace_id,
            listing_id=listing.id,
            version=payload.version,
            skill_content=template.skill_content,
            graph_data=payload.graph_data,
            changelog="Initial release",
        )

        logger.info(
            "[Marketplace] Published listing=%s name=%s by=%s v%s",
            listing.id,
            payload.name,
            payload.author,
            payload.version,
        )
        return listing

    async def create_version(
        self, payload: CreateVersionPayload
    ) -> SkillVersion:
        """Create a new version for an existing listing.

        Validates that the new version is strictly greater than the
        current listing version using semver tuple comparison.

        Args:
            payload: Version creation parameters.

        Returns:
            Newly created SkillVersion.

        Raises:
            NotFoundError: If the listing does not exist.
            ValidationError: If the new version is not higher than current.
        """
        listing = await self._listing_repo.get_by_id(payload.listing_id)
        if listing is None:
            raise NotFoundError("Marketplace listing not found")

        # Validate semver ordering
        current = _parse_semver(listing.version)
        new = _parse_semver(payload.version)
        if new <= current:
            raise ValidationError(
                f"New version {payload.version} must be higher than "
                f"current version {listing.version}"
            )

        # Create the version
        version = await self._version_repo.create(
            workspace_id=payload.workspace_id,
            listing_id=payload.listing_id,
            version=payload.version,
            skill_content=payload.skill_content,
            changelog=payload.changelog,
            graph_data=payload.graph_data,
        )

        # Update the listing's current version
        listing.version = payload.version
        await self._session.flush()

        logger.info(
            "[Marketplace] New version listing=%s v%s",
            payload.listing_id,
            payload.version,
        )
        return version

    async def search(self, payload: SearchPayload) -> SearchResult:
        """Search marketplace listings with optional filters.

        Delegates to repository search/category methods, applies
        min_rating post-filter, and returns paginated results.

        Args:
            payload: Search parameters.

        Returns:
            SearchResult with filtered items, total count, and has_next flag.
        """
        if payload.query:
            items_raw = await self._listing_repo.search(
                payload.query,
                category=payload.category,
                limit=payload.limit + 1,  # fetch one extra to detect has_next
                offset=payload.offset,
            )
        elif payload.category:
            items_raw = await self._listing_repo.get_by_category(
                payload.category,
                limit=payload.limit + 1,
                offset=payload.offset,
            )
        else:
            # No query or category — search with empty string returns all
            items_raw = await self._listing_repo.search(
                "",
                limit=payload.limit + 1,
                offset=payload.offset,
            )

        items = list(items_raw)

        # Apply min_rating post-filter
        if payload.min_rating is not None:
            items = [
                item
                for item in items
                if item.avg_rating is not None and item.avg_rating >= payload.min_rating
            ]

        # Detect has_next before trimming
        has_next = len(items) > payload.limit
        if has_next:
            items = items[: payload.limit]

        return SearchResult(
            items=items,
            total=len(items),
            has_next=has_next,
        )

    async def get_listing(self, listing_id: UUID) -> SkillMarketplaceListing:
        """Get a marketplace listing by ID.

        Args:
            listing_id: The listing UUID.

        Returns:
            The requested listing.

        Raises:
            NotFoundError: If the listing does not exist.
        """
        listing = await self._listing_repo.get_by_id(listing_id)
        if listing is None:
            raise NotFoundError("Marketplace listing not found")
        return listing

    async def get_versions(self, listing_id: UUID) -> Sequence[SkillVersion]:
        """Get version history for a listing.

        Args:
            listing_id: The parent listing UUID.

        Returns:
            Version history, newest first.
        """
        return await self._version_repo.get_by_listing(listing_id)

    async def get_workspace_listings(
        self, workspace_id: UUID
    ) -> Sequence[SkillMarketplaceListing]:
        """Get all listings published by a workspace.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            All non-deleted listings for the workspace.
        """
        return await self._listing_repo.get_by_workspace(workspace_id)


__all__ = [
    "CreateVersionPayload",
    "MarketplaceService",
    "PublishListingPayload",
    "SearchPayload",
    "SearchResult",
]
