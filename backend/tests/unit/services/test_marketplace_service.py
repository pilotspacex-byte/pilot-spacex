"""Tests for MarketplaceService — publish, search, version management.

Phase 054, Plan 01, Task 2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.application.services.skill.marketplace_service import (
    CreateVersionPayload,
    MarketplaceService,
    PublishListingPayload,
    SearchPayload,
    SearchResult,
)
from pilot_space.domain.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)


_WORKSPACE_ID = uuid4()
_USER_ID = uuid4()
_TEMPLATE_ID = uuid4()
_LISTING_ID = uuid4()


def _make_listing(**overrides) -> MagicMock:
    """Create a mock marketplace listing."""
    listing = MagicMock()
    listing.id = overrides.get("id", _LISTING_ID)
    listing.workspace_id = overrides.get("workspace_id", _WORKSPACE_ID)
    listing.name = overrides.get("name", "Test Skill")
    listing.description = overrides.get("description", "A test skill")
    listing.author = overrides.get("author", "Alice")
    listing.category = overrides.get("category", "development")
    listing.version = overrides.get("version", "1.0.0")
    listing.download_count = overrides.get("download_count", 10)
    listing.avg_rating = overrides.get("avg_rating", 4.5)
    listing.tags = overrides.get("tags", ["python"])
    listing.icon = overrides.get("icon", "Wand2")
    listing.is_deleted = False
    return listing


def _make_version(**overrides) -> MagicMock:
    """Create a mock skill version."""
    version = MagicMock()
    version.id = overrides.get("id", uuid4())
    version.listing_id = overrides.get("listing_id", _LISTING_ID)
    version.version = overrides.get("version", "1.0.0")
    version.skill_content = overrides.get("skill_content", "# Skill content")
    version.changelog = overrides.get("changelog", None)
    version.graph_data = overrides.get("graph_data", None)
    version.created_at = datetime.now(tz=timezone.utc)
    return version


def _make_template(**overrides) -> MagicMock:
    """Create a mock skill template."""
    tpl = MagicMock()
    tpl.id = overrides.get("id", _TEMPLATE_ID)
    tpl.workspace_id = overrides.get("workspace_id", _WORKSPACE_ID)
    tpl.name = overrides.get("name", "Template Skill")
    tpl.skill_content = overrides.get("skill_content", "# Template\nContent here")
    return tpl


@pytest.fixture
def session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(session: AsyncMock) -> MarketplaceService:
    return MarketplaceService(session)


class TestPublishListing:
    """Tests for MarketplaceService.publish_listing."""

    @pytest.mark.asyncio
    async def test_creates_listing_and_version(self, service: MarketplaceService) -> None:
        template = _make_template()
        listing = _make_listing()
        version = _make_version()

        with (
            patch.object(service, "_template_repo") as mock_tpl_repo,
            patch.object(service, "_listing_repo") as mock_listing_repo,
            patch.object(service, "_version_repo") as mock_version_repo,
        ):
            mock_tpl_repo.get_by_id = AsyncMock(return_value=template)
            mock_listing_repo.create = AsyncMock(return_value=listing)
            mock_version_repo.create = AsyncMock(return_value=version)

            payload = PublishListingPayload(
                workspace_id=_WORKSPACE_ID,
                skill_template_id=_TEMPLATE_ID,
                user_id=_USER_ID,
                name="Test Skill",
                description="A test skill",
                author="Alice",
                category="development",
                version="1.0.0",
            )
            result = await service.publish_listing(payload)

            assert result.name == "Test Skill"
            mock_listing_repo.create.assert_awaited_once()
            mock_version_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_template(self, service: MarketplaceService) -> None:
        with patch.object(service, "_template_repo") as mock_tpl_repo:
            mock_tpl_repo.get_by_id = AsyncMock(return_value=None)

            payload = PublishListingPayload(
                workspace_id=_WORKSPACE_ID,
                skill_template_id=uuid4(),
                user_id=_USER_ID,
                name="Test",
                description="d",
                author="a",
                category="c",
                version="1.0.0",
            )
            with pytest.raises(NotFoundError):
                await service.publish_listing(payload)

    @pytest.mark.asyncio
    async def test_raises_conflict_on_duplicate(self, service: MarketplaceService) -> None:
        from sqlalchemy.exc import IntegrityError

        template = _make_template()

        with (
            patch.object(service, "_template_repo") as mock_tpl_repo,
            patch.object(service, "_listing_repo") as mock_listing_repo,
        ):
            mock_tpl_repo.get_by_id = AsyncMock(return_value=template)
            mock_listing_repo.create = AsyncMock(
                side_effect=IntegrityError("", {}, Exception("duplicate"))
            )

            payload = PublishListingPayload(
                workspace_id=_WORKSPACE_ID,
                skill_template_id=_TEMPLATE_ID,
                user_id=_USER_ID,
                name="Duplicate",
                description="d",
                author="a",
                category="c",
                version="1.0.0",
            )
            with pytest.raises(ConflictError):
                await service.publish_listing(payload)


class TestCreateVersion:
    """Tests for MarketplaceService.create_version."""

    @pytest.mark.asyncio
    async def test_succeeds_for_higher_version(self, service: MarketplaceService) -> None:
        listing = _make_listing(version="1.0.0")
        new_version = _make_version(version="2.0.0")

        with (
            patch.object(service, "_listing_repo") as mock_listing_repo,
            patch.object(service, "_version_repo") as mock_version_repo,
        ):
            mock_listing_repo.get_by_id = AsyncMock(return_value=listing)
            mock_version_repo.create = AsyncMock(return_value=new_version)

            payload = CreateVersionPayload(
                workspace_id=_WORKSPACE_ID,
                listing_id=_LISTING_ID,
                version="2.0.0",
                skill_content="# Updated",
            )
            result = await service.create_version(payload)
            assert result.version == "2.0.0"
            mock_version_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_validates_semver_ordering_rejects_lower(self, service: MarketplaceService) -> None:
        listing = _make_listing(version="1.0.0")

        with patch.object(service, "_listing_repo") as mock_listing_repo:
            mock_listing_repo.get_by_id = AsyncMock(return_value=listing)

            payload = CreateVersionPayload(
                workspace_id=_WORKSPACE_ID,
                listing_id=_LISTING_ID,
                version="0.9.0",
                skill_content="# Old",
            )
            with pytest.raises(ValidationError):
                await service.create_version(payload)

    @pytest.mark.asyncio
    async def test_validates_semver_ordering_rejects_equal(self, service: MarketplaceService) -> None:
        listing = _make_listing(version="1.0.0")

        with patch.object(service, "_listing_repo") as mock_listing_repo:
            mock_listing_repo.get_by_id = AsyncMock(return_value=listing)

            payload = CreateVersionPayload(
                workspace_id=_WORKSPACE_ID,
                listing_id=_LISTING_ID,
                version="1.0.0",
                skill_content="# Same",
            )
            with pytest.raises(ValidationError):
                await service.create_version(payload)

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_listing(self, service: MarketplaceService) -> None:
        with patch.object(service, "_listing_repo") as mock_listing_repo:
            mock_listing_repo.get_by_id = AsyncMock(return_value=None)

            payload = CreateVersionPayload(
                workspace_id=_WORKSPACE_ID,
                listing_id=uuid4(),
                version="1.0.0",
                skill_content="# Content",
            )
            with pytest.raises(NotFoundError):
                await service.create_version(payload)


class TestSearch:
    """Tests for MarketplaceService.search."""

    @pytest.mark.asyncio
    async def test_returns_paginated_results(self, service: MarketplaceService) -> None:
        listings = [_make_listing(name=f"Skill {i}") for i in range(3)]

        with patch.object(service, "_listing_repo") as mock_listing_repo:
            mock_listing_repo.search = AsyncMock(return_value=listings)

            payload = SearchPayload(query="Skill", limit=20, offset=0)
            result = await service.search(payload)

            assert isinstance(result, SearchResult)
            assert len(result.items) == 3

    @pytest.mark.asyncio
    async def test_filters_by_category(self, service: MarketplaceService) -> None:
        listings = [_make_listing(category="design")]

        with patch.object(service, "_listing_repo") as mock_listing_repo:
            mock_listing_repo.get_by_category = AsyncMock(return_value=listings)

            payload = SearchPayload(category="design", limit=20, offset=0)
            result = await service.search(payload)

            assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_filters_by_min_rating(self, service: MarketplaceService) -> None:
        listings = [
            _make_listing(avg_rating=4.5),
            _make_listing(avg_rating=3.0),
            _make_listing(avg_rating=None),
        ]

        with patch.object(service, "_listing_repo") as mock_listing_repo:
            mock_listing_repo.search = AsyncMock(return_value=listings)

            payload = SearchPayload(query="test", min_rating=4.0, limit=20, offset=0)
            result = await service.search(payload)

            assert len(result.items) == 1
            assert result.items[0].avg_rating == 4.5


class TestGetListing:
    """Tests for MarketplaceService.get_listing."""

    @pytest.mark.asyncio
    async def test_returns_listing(self, service: MarketplaceService) -> None:
        listing = _make_listing()

        with patch.object(service, "_listing_repo") as mock_listing_repo:
            mock_listing_repo.get_by_id = AsyncMock(return_value=listing)
            result = await service.get_listing(_LISTING_ID)
            assert result.name == "Test Skill"

    @pytest.mark.asyncio
    async def test_raises_not_found(self, service: MarketplaceService) -> None:
        with patch.object(service, "_listing_repo") as mock_listing_repo:
            mock_listing_repo.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(NotFoundError):
                await service.get_listing(uuid4())
