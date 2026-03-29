"""Pydantic schemas for marketplace API endpoints.

Provides request/response models for marketplace listings, versions,
and search with semver validation.

Source: Phase 054, P54-01
"""

from __future__ import annotations

import re
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator

from pilot_space.api.v1.schemas.base import BaseSchema, EntitySchema, PaginatedResponse

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _validate_semver(v: str) -> str:
    """Validate that a version string matches X.Y.Z semver format."""
    if not _SEMVER_RE.match(v):
        msg = "Version must be in semver format: X.Y.Z (e.g., 1.0.0)"
        raise ValueError(msg)
    return v


class MarketplaceListingResponse(EntitySchema):
    """Response schema for a marketplace listing.

    Serializes all listing fields including computed metrics
    (download_count, avg_rating).
    """

    workspace_id: UUID
    name: str
    description: str
    long_description: str | None = None
    author: str
    icon: str
    category: str
    tags: list[str] = Field(default_factory=list)
    version: str
    download_count: int = 0
    avg_rating: float | None = None
    screenshots: list[str] | None = None
    graph_data: dict[str, Any] | None = None
    published_by: UUID | None = None


class MarketplaceListingCreate(BaseSchema):
    """Request schema for creating a marketplace listing.

    Validates name length (3-100), non-empty description/author,
    and semver version format.
    """

    name: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=1)
    long_description: str | None = None
    author: str = Field(min_length=1, max_length=100)
    category: str
    version: str
    icon: str = "Wand2"
    tags: list[str] = Field(default_factory=list)
    screenshots: list[str] | None = None
    graph_data: dict[str, Any] | None = None

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Ensure version matches semver X.Y.Z format."""
        return _validate_semver(v)


class MarketplaceVersionCreate(BaseSchema):
    """Request schema for creating a new version of a listing.

    Validates semver format and non-empty skill content.
    """

    version: str
    skill_content: str = Field(min_length=1)
    changelog: str | None = None
    graph_data: dict[str, Any] | None = None

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Ensure version matches semver X.Y.Z format."""
        return _validate_semver(v)


class MarketplaceVersionResponse(EntitySchema):
    """Response schema for a skill version."""

    listing_id: UUID
    version: str
    skill_content: str
    changelog: str | None = None
    graph_data: dict[str, Any] | None = None


class MarketplaceSearchParams(BaseSchema):
    """Query parameters for marketplace search.

    Supports text query, category filter, minimum rating,
    and sort mode (popular/newest/top_rated).
    """

    query: str | None = None
    category: str | None = None
    min_rating: float | None = Field(default=None, ge=1, le=5)
    sort: Literal["popular", "newest", "top_rated"] = "popular"
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class MarketplaceSearchResponse(PaginatedResponse[MarketplaceListingResponse]):
    """Paginated search response for marketplace listings."""


class ReviewCreateRequest(BaseSchema):
    """Request body for creating or updating a review."""

    rating: int = Field(ge=1, le=5)
    review_text: str | None = None


class ReviewResponse(EntitySchema):
    """Response schema for a single review."""

    listing_id: UUID
    user_id: UUID
    rating: int
    review_text: str | None = None


class ReviewListResponse(BaseSchema):
    """Paginated list of reviews."""

    items: list[ReviewResponse]
    total: int
    has_next: bool


class InstallResponse(BaseSchema):
    """Response schema for install endpoint."""

    skill_template_id: UUID
    already_installed: bool


class UpdateCheckResponse(BaseSchema):
    """Response schema for a single update check result."""

    template_id: UUID
    template_name: str
    installed_version: str
    available_version: str
    listing_id: UUID


class UpdateApplyResponse(BaseSchema):
    """Response schema for applying an update."""

    updated: bool
    new_version: str
    template_id: UUID


class PublishListingRequest(BaseSchema):
    """Request body for publishing a skill to marketplace."""

    skill_template_id: UUID
    listing: MarketplaceListingCreate


__all__ = [
    "InstallResponse",
    "MarketplaceListingCreate",
    "MarketplaceListingResponse",
    "MarketplaceSearchParams",
    "MarketplaceSearchResponse",
    "MarketplaceVersionCreate",
    "MarketplaceVersionResponse",
    "PublishListingRequest",
    "ReviewCreateRequest",
    "ReviewListResponse",
    "ReviewResponse",
    "UpdateApplyResponse",
    "UpdateCheckResponse",
]
