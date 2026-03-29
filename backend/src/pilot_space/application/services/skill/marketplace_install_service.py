"""Service for installing marketplace skills into workspace skill templates.

Handles one-click install, idempotent re-install, version comparison for
update detection, and update application.

Source: Phase 054, P054-02
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, select

from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.models.skill_template import SkillTemplate
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
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


@dataclass
class InstallPayload:
    """Input payload for installing a marketplace listing."""

    workspace_id: UUID
    listing_id: UUID
    user_id: UUID


@dataclass
class InstallResult:
    """Result of an install operation."""

    skill_template: SkillTemplate  # The created or existing template
    already_installed: bool  # True if was already installed


@dataclass
class UpdateCheckResult:
    """A single template that has an available update."""

    template_id: UUID
    template_name: str
    installed_version: str
    available_version: str
    listing_id: UUID


def _parse_semver(version: str) -> tuple[int, ...]:
    """Parse a semver string into a comparable tuple.

    Args:
        version: Semver string like "1.2.3".

    Returns:
        Tuple of integers for comparison.
    """
    try:
        return tuple(int(p) for p in version.split("."))
    except (ValueError, AttributeError):
        return (0,)


class MarketplaceInstallService:
    """Service for installing marketplace listings as workspace skill templates.

    Handles:
    - One-click install from marketplace listing
    - Idempotent re-install (returns existing if already installed)
    - Update detection (compares installed vs. latest version)
    - Update application (pulls latest content and version)

    Args:
        session: Request-scoped async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._listing_repo = SkillMarketplaceListingRepository(session)
        self._template_repo = SkillTemplateRepository(session)
        self._version_repo = SkillVersionRepository(session)

    async def _get_existing_install(
        self, workspace_id: UUID, listing_id: UUID
    ) -> SkillTemplate | None:
        """Check if a listing is already installed in the workspace.

        Args:
            workspace_id: The workspace UUID.
            listing_id: The marketplace listing UUID.

        Returns:
            Existing SkillTemplate if found, None otherwise.
        """
        query = select(SkillTemplate).where(
            and_(
                SkillTemplate.workspace_id == workspace_id,
                SkillTemplate.marketplace_listing_id == listing_id,
                SkillTemplate.is_deleted == False,  # noqa: E712
            )
        )
        result = await self._session.execute(query)
        return result.scalars().first()

    async def install(self, payload: InstallPayload) -> InstallResult:
        """Install a marketplace listing into the workspace as a skill template.

        Idempotent: if already installed, returns existing template.

        Args:
            payload: Install parameters (workspace_id, listing_id, user_id).

        Returns:
            InstallResult with the template and whether it was already installed.

        Raises:
            NotFoundError: If listing not found or has no published versions.
        """
        # Get listing
        listing = await self._listing_repo.get_by_id(payload.listing_id)
        if listing is None:
            raise NotFoundError("Marketplace listing not found")

        # Check idempotency
        existing = await self._get_existing_install(payload.workspace_id, payload.listing_id)
        if existing is not None:
            logger.info(
                "[MarketplaceInstall] Already installed listing=%s workspace=%s",
                payload.listing_id,
                payload.workspace_id,
            )
            return InstallResult(skill_template=existing, already_installed=True)

        # Get latest version content
        latest_version = await self._version_repo.get_latest_by_listing(payload.listing_id)
        if latest_version is None:
            raise NotFoundError("Marketplace listing has no published version")

        # Create skill template from listing
        template = SkillTemplate(
            workspace_id=payload.workspace_id,
            name=listing.name,
            description=listing.description,
            skill_content=latest_version.skill_content,
            icon=listing.icon,
            source="marketplace",
            marketplace_listing_id=listing.id,
            installed_version=latest_version.version,
            is_active=True,
            created_by=payload.user_id,
        )
        self._session.add(template)
        await self._session.flush()
        await self._session.refresh(template)

        # Increment download count
        await self._listing_repo.increment_download_count(payload.listing_id)

        logger.info(
            "[MarketplaceInstall] Installed listing=%s as template=%s workspace=%s",
            payload.listing_id,
            template.id,
            payload.workspace_id,
        )
        return InstallResult(skill_template=template, already_installed=False)

    async def check_updates(self, workspace_id: UUID) -> list[UpdateCheckResult]:
        """Check for available updates on installed marketplace templates.

        Compares each installed template's version against the listing's
        current version using semver tuple comparison.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            List of UpdateCheckResult for templates with available updates.
        """
        # Get all marketplace-installed templates in this workspace
        query = select(SkillTemplate).where(
            and_(
                SkillTemplate.workspace_id == workspace_id,
                SkillTemplate.marketplace_listing_id.isnot(None),
                SkillTemplate.is_deleted == False,  # noqa: E712
            )
        )
        result = await self._session.execute(query)
        templates = result.scalars().all()

        updates: list[UpdateCheckResult] = []
        for template in templates:
            listing = await self._listing_repo.get_by_id(template.marketplace_listing_id)
            if listing is None:
                continue

            installed = _parse_semver(template.installed_version or "0.0.0")
            available = _parse_semver(listing.version)

            if installed < available:
                updates.append(
                    UpdateCheckResult(
                        template_id=template.id,
                        template_name=template.name,
                        installed_version=template.installed_version or "0.0.0",
                        available_version=listing.version,
                        listing_id=listing.id,
                    )
                )

        return updates

    async def update_installed(
        self, workspace_id: UUID, template_id: UUID
    ) -> SkillTemplate:
        """Update an installed marketplace template to the latest version.

        Args:
            workspace_id: The workspace UUID (for authorization).
            template_id: The template UUID to update.

        Returns:
            Updated SkillTemplate with new content and version.

        Raises:
            NotFoundError: If template not found or not a marketplace install.
        """
        template = await self._template_repo.get_by_id(template_id)
        if template is None or template.marketplace_listing_id is None:
            raise NotFoundError("Installed marketplace template not found")

        latest_version = await self._version_repo.get_latest_by_listing(
            template.marketplace_listing_id
        )
        if latest_version is None:
            raise NotFoundError("No versions available for update")

        template.skill_content = latest_version.skill_content
        template.installed_version = latest_version.version
        await self._session.flush()
        await self._session.refresh(template)

        logger.info(
            "[MarketplaceInstall] Updated template=%s to version=%s",
            template_id,
            latest_version.version,
        )
        return template


__all__ = [
    "InstallPayload",
    "InstallResult",
    "MarketplaceInstallService",
    "UpdateCheckResult",
]
