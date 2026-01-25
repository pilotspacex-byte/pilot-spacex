"""Base Pydantic schemas for API responses.

Provides common response models and pagination schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration.

    Uses camelCase for JSON serialization to match frontend conventions.
    Accepts both camelCase and snake_case for input (populate_by_name=True).
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class EntitySchema(TimestampSchema):
    """Schema for database entities with ID and timestamps."""

    id: UUID = Field(description="Unique identifier")


class SoftDeleteSchema(EntitySchema):
    """Schema for soft-deletable entities."""

    is_deleted: bool = Field(default=False, description="Soft delete flag")
    deleted_at: datetime | None = Field(default=None, description="Deletion timestamp")


class PaginationParams(BaseSchema):
    """Pagination parameters for list endpoints."""

    cursor: str | None = Field(default=None, description="Cursor for pagination")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(
        default="desc",
        description="Sort direction (asc or desc)",
        pattern="^(asc|desc)$",
    )


class PaginatedResponse[T](BaseSchema):
    """Paginated list response.

    Attributes:
        items: List of items for current page.
        total: Total count of items matching the query.
        next_cursor: Cursor for fetching next page.
        prev_cursor: Cursor for fetching previous page.
        has_next: Whether more items exist.
        has_prev: Whether previous items exist.
        page_size: Number of items per page.
    """

    items: list[T]
    total: int = Field(ge=0, description="Total item count")
    next_cursor: str | None = Field(default=None, description="Next page cursor")
    prev_cursor: str | None = Field(default=None, description="Previous page cursor")
    has_next: bool = Field(default=False, description="Has more items")
    has_prev: bool = Field(default=False, description="Has previous items")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class ErrorResponse(BaseSchema):
    """RFC 7807 Problem Details error response.

    Attributes:
        type: URI reference identifying the problem type.
        title: Short, human-readable summary.
        status: HTTP status code.
        detail: Human-readable explanation.
        instance: URI identifying the specific occurrence.
    """

    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type",
    )
    title: str = Field(description="Short, human-readable summary")
    status: int = Field(description="HTTP status code")
    detail: str | None = Field(default=None, description="Human-readable explanation")
    instance: str | None = Field(
        default=None,
        description="URI identifying the specific occurrence",
    )
    errors: list[dict[str, Any]] | None = Field(
        default=None,
        description="Validation errors (for 422 responses)",
    )


class SuccessResponse(BaseSchema):
    """Generic success response."""

    success: bool = Field(default=True, description="Operation success flag")
    message: str | None = Field(default=None, description="Success message")


class DeleteResponse(SuccessResponse):
    """Response for delete operations."""

    id: UUID = Field(description="ID of deleted resource")


class BulkResponse[T](BaseSchema):
    """Response for bulk operations.

    Attributes:
        succeeded: Items that were processed successfully.
        failed: Items that failed processing.
        total_processed: Total number of items processed.
    """

    succeeded: list[T] = Field(default_factory=list, description="Successfully processed items")  # type: ignore[var-annotated]
    failed: list[dict[str, Any]] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list, description="Failed items with errors"
    )  # type: ignore[var-annotated]
    total_processed: int = Field(ge=0, description="Total items processed")

    @property
    def success_count(self) -> int:
        """Count of successful items."""
        return len(self.succeeded)

    @property
    def failure_count(self) -> int:
        """Count of failed items."""
        return len(self.failed)


class HealthResponse(BaseSchema):
    """Health check response."""

    status: str = Field(description="Health status")
    version: str = Field(description="Application version")
    environment: str = Field(description="Current environment")
    checks: dict[str, bool] = Field(
        default_factory=dict,
        description="Individual health checks",
    )
