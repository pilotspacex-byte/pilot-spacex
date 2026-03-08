"""Pydantic schemas for audit log API endpoints.

Provides:
- AuditLogResponse: Response schema mirroring AuditLog model fields
- AuditFilterParams: Query parameters for filtering the audit log list
- AuditExportParams: Query parameters for the streaming export endpoint
- AuditRetentionRequest: Body schema for PATCH retention endpoint

Requirements: AUDIT-03, AUDIT-04, AUDIT-05
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema
from pilot_space.infrastructure.database.models.audit_log import ActorType


class AuditLogResponse(BaseSchema):
    """Response schema for a single audit log entry.

    Mirrors the AuditLog SQLAlchemy model fields. Immutable — no write
    operations are exposed via the audit API.

    Attributes:
        id: UUID primary key.
        workspace_id: Owning workspace UUID.
        actor_id: UUID of the acting user/system, or None for system actions.
        actor_type: ActorType enum (USER, SYSTEM, AI).
        action: Dot-notation action string e.g. "issue.create".
        resource_type: Resource category e.g. "issue", "note".
        resource_id: UUID of the affected resource, or None.
        payload: JSONB diff {"before": {...}, "after": {...}}.
        ai_input: Raw AI input (only for AI actor entries).
        ai_output: Raw AI output (only for AI actor entries).
        ai_model: Model identifier.
        ai_token_cost: Token count consumed.
        ai_rationale: AI's stated rationale for the action.
        ip_address: Client IP address.
        created_at: Timestamp of the action.
        updated_at: Always equals created_at for immutable records.
    """

    id: UUID = Field(description="Audit log entry UUID")
    workspace_id: UUID = Field(description="Owning workspace UUID")
    actor_id: UUID | None = Field(default=None, description="Actor user UUID")
    actor_type: ActorType = Field(description="Actor type (USER, SYSTEM, AI)")
    action: str = Field(description="Dot-notation action string")
    resource_type: str = Field(description="Resource category")
    resource_id: UUID | None = Field(default=None, description="Affected resource UUID")
    payload: dict[str, Any] | None = Field(default=None, description="Before/after diff payload")
    ai_input: dict[str, Any] | None = Field(
        default=None, description="Raw AI input (AI actor only)"
    )
    ai_output: dict[str, Any] | None = Field(
        default=None, description="Raw AI output (AI actor only)"
    )
    ai_model: str | None = Field(default=None, description="Model identifier")
    ai_token_cost: int | None = Field(default=None, description="Token count consumed")
    ai_rationale: str | None = Field(default=None, description="AI rationale for the action")
    ip_address: str | None = Field(default=None, description="Client IP address")
    created_at: datetime = Field(description="Timestamp of the action")
    updated_at: datetime = Field(description="Last updated (equals created_at for audit records)")


class AuditFilterParams(BaseSchema):
    """Query parameters for filtering the audit log list or export.

    All filters are optional and can be combined. Filters are ANDed together.

    Attributes:
        actor_id: Filter by actor UUID.
        action: Filter by exact action string e.g. "issue.create".
        resource_type: Filter by resource category.
        start_date: Inclusive lower bound for created_at.
        end_date: Inclusive upper bound for created_at.
        cursor: Opaque cursor for keyset pagination (list endpoint only).
        page_size: Items per page (list endpoint only, 1-500).
    """

    actor_id: UUID | None = Field(default=None, description="Filter by actor UUID")
    action: str | None = Field(default=None, description="Filter by exact action string")
    resource_type: str | None = Field(default=None, description="Filter by resource category")
    start_date: datetime | None = Field(
        default=None, description="Inclusive lower bound for created_at"
    )
    end_date: datetime | None = Field(
        default=None, description="Inclusive upper bound for created_at"
    )
    cursor: str | None = Field(
        default=None, description="Opaque cursor for next page (base64-encoded)"
    )
    page_size: int = Field(default=50, ge=1, le=500, description="Items per page (max 500)")


class AuditExportParams(BaseSchema):
    """Query parameters for the streaming export endpoint.

    Extends filter params with export format selection.

    Attributes:
        format: Export format — "csv" or "json".
        actor_id: Filter by actor UUID.
        action: Filter by exact action string.
        resource_type: Filter by resource category.
        start_date: Inclusive lower bound for created_at.
        end_date: Inclusive upper bound for created_at.
    """

    format: Literal["csv", "json"] = Field(default="json", description="Export format: csv or json")
    actor_id: UUID | None = Field(default=None, description="Filter by actor UUID")
    action: str | None = Field(default=None, description="Filter by exact action string")
    resource_type: str | None = Field(default=None, description="Filter by resource category")
    start_date: datetime | None = Field(
        default=None, description="Inclusive lower bound for created_at"
    )
    end_date: datetime | None = Field(
        default=None, description="Inclusive upper bound for created_at"
    )


class AuditRetentionRequest(BaseSchema):
    """Request body for PATCH retention endpoint.

    Attributes:
        audit_retention_days: Number of days to retain audit logs.
            Must be between 1 and 3650 (10 years).
    """

    audit_retention_days: int = Field(
        ge=1,
        le=3650,
        description="Number of days to retain audit logs (1-3650)",
    )


class AuditLogPageResponse(BaseSchema):
    """Paginated response for audit log list endpoint.

    Attributes:
        items: Audit log entries for the current page.
        has_next: Whether additional rows exist after this page.
        next_cursor: Opaque cursor for the next page, None if no more pages.
        page_size: Requested page size.
    """

    items: list[AuditLogResponse]
    has_next: bool = Field(default=False, description="Whether more items exist")
    next_cursor: str | None = Field(default=None, description="Next page cursor")
    page_size: int = Field(description="Requested page size")


__all__ = [
    "AuditExportParams",
    "AuditFilterParams",
    "AuditLogPageResponse",
    "AuditLogResponse",
    "AuditRetentionRequest",
]
