"""Tests for marketplace Pydantic schemas — semver validation, field constraints.

Phase 054, Plan 01, Task 1 (RED).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pilot_space.api.v1.schemas.marketplace import (
    MarketplaceListingCreate,
    MarketplaceListingResponse,
    MarketplaceSearchParams,
    MarketplaceSearchResponse,
    MarketplaceVersionCreate,
    MarketplaceVersionResponse,
)


class TestMarketplaceListingResponse:
    """MarketplaceListingResponse serialization tests."""

    def test_serializes_all_listing_fields(self) -> None:
        now = datetime.now(tz=timezone.utc)
        uid = uuid4()
        ws_id = uuid4()
        resp = MarketplaceListingResponse(
            id=uid,
            workspace_id=ws_id,
            name="Test Skill",
            description="A test skill",
            long_description="Extended description",
            author="Alice",
            icon="Wand2",
            category="development",
            tags=["python", "testing"],
            version="1.0.0",
            download_count=42,
            avg_rating=4.5,
            screenshots=["https://example.com/shot.png"],
            graph_data={"nodes": []},
            published_by=uid,
            created_at=now,
            updated_at=now,
        )
        data = resp.model_dump(by_alias=True)
        assert data["name"] == "Test Skill"
        assert data["downloadCount"] == 42
        assert data["avgRating"] == 4.5
        assert data["tags"] == ["python", "testing"]

    def test_camel_case_serialization(self) -> None:
        now = datetime.now(tz=timezone.utc)
        resp = MarketplaceListingResponse(
            id=uuid4(),
            workspace_id=uuid4(),
            name="X",
            description="d",
            author="a",
            icon="Wand2",
            category="c",
            tags=[],
            version="1.0.0",
            download_count=0,
            avg_rating=None,
            published_by=None,
            created_at=now,
            updated_at=now,
        )
        data = resp.model_dump(by_alias=True)
        assert "downloadCount" in data
        assert "avgRating" in data
        assert "workspaceId" in data


class TestMarketplaceListingCreate:
    """MarketplaceListingCreate validation tests."""

    def test_valid_listing(self) -> None:
        listing = MarketplaceListingCreate(
            name="My Skill",
            description="Does things",
            author="Bob",
            category="productivity",
            version="1.0.0",
        )
        assert listing.name == "My Skill"
        assert listing.icon == "Wand2"
        assert listing.tags == []

    def test_name_too_short_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketplaceListingCreate(
                name="ab",
                description="d",
                author="a",
                category="c",
                version="1.0.0",
            )

    def test_name_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketplaceListingCreate(
                name="x" * 101,
                description="d",
                author="a",
                category="c",
                version="1.0.0",
            )

    def test_semver_valid_accepts(self) -> None:
        listing = MarketplaceListingCreate(
            name="Skill",
            description="d",
            author="a",
            category="c",
            version="0.1.2",
        )
        assert listing.version == "0.1.2"

    def test_semver_rejects_incomplete(self) -> None:
        with pytest.raises(ValidationError):
            MarketplaceListingCreate(
                name="Skill",
                description="d",
                author="a",
                category="c",
                version="1.0",
            )

    def test_semver_rejects_non_numeric(self) -> None:
        with pytest.raises(ValidationError):
            MarketplaceListingCreate(
                name="Skill",
                description="d",
                author="a",
                category="c",
                version="abc",
            )

    def test_semver_rejects_extra_segments(self) -> None:
        with pytest.raises(ValidationError):
            MarketplaceListingCreate(
                name="Skill",
                description="d",
                author="a",
                category="c",
                version="1.0.0.0",
            )


class TestMarketplaceVersionCreate:
    """MarketplaceVersionCreate validation tests."""

    def test_valid_version(self) -> None:
        vc = MarketplaceVersionCreate(
            version="2.0.0",
            skill_content="# Skill\nContent here",
        )
        assert vc.version == "2.0.0"
        assert vc.changelog is None

    def test_semver_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            MarketplaceVersionCreate(
                version="bad",
                skill_content="content",
            )

    def test_empty_skill_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketplaceVersionCreate(
                version="1.0.0",
                skill_content="",
            )


class TestMarketplaceVersionResponse:
    """MarketplaceVersionResponse serialization tests."""

    def test_serializes_version_fields(self) -> None:
        now = datetime.now(tz=timezone.utc)
        resp = MarketplaceVersionResponse(
            id=uuid4(),
            listing_id=uuid4(),
            version="1.2.3",
            skill_content="# Skill",
            changelog="Fixed bug",
            graph_data=None,
            created_at=now,
            updated_at=now,
        )
        data = resp.model_dump(by_alias=True)
        assert data["listingId"] is not None
        assert data["skillContent"] == "# Skill"


class TestMarketplaceSearchParams:
    """MarketplaceSearchParams validation tests."""

    def test_defaults(self) -> None:
        params = MarketplaceSearchParams()
        assert params.sort == "popular"
        assert params.limit == 20
        assert params.offset == 0
        assert params.query is None

    def test_min_rating_range(self) -> None:
        params = MarketplaceSearchParams(min_rating=3.5)
        assert params.min_rating == 3.5

    def test_min_rating_below_1_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketplaceSearchParams(min_rating=0.5)

    def test_min_rating_above_5_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketplaceSearchParams(min_rating=5.5)

    def test_limit_max_100(self) -> None:
        with pytest.raises(ValidationError):
            MarketplaceSearchParams(limit=101)


class TestMarketplaceSearchResponse:
    """MarketplaceSearchResponse pagination tests."""

    def test_empty_search_response(self) -> None:
        resp = MarketplaceSearchResponse(
            items=[],
            total=0,
            has_next=False,
            page_size=20,
        )
        assert resp.total == 0
        assert resp.items == []
