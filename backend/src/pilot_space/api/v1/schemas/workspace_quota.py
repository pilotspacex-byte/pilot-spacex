"""Pydantic schemas for workspace quota API.

TENANT-03: Per-workspace rate limit and storage quota schemas.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator


class QuotaResponse(BaseModel):
    """Response for GET /settings/quota."""

    rate_limit_standard_rpm: int | None
    rate_limit_ai_rpm: int | None
    storage_quota_mb: int | None
    storage_used_bytes: int
    storage_used_mb: float


class QuotaUpdateRequest(BaseModel):
    """Request body for PATCH /settings/quota.

    All fields are optional — send only the fields you want to change.
    Pass null to remove a custom limit (revert to system default).
    """

    rate_limit_standard_rpm: int | None = None
    rate_limit_ai_rpm: int | None = None
    storage_quota_mb: int | None = None

    @field_validator(
        "rate_limit_standard_rpm", "rate_limit_ai_rpm", "storage_quota_mb", mode="before"
    )
    @classmethod
    def must_be_positive_or_none(cls, v: Any) -> Any:
        """Validate that numeric fields are positive integers or None."""
        if v is not None and (not isinstance(v, int) or v <= 0):
            raise ValueError("Must be a positive integer or null")
        return v


class RecalculateResponse(BaseModel):
    """Response for POST /settings/quota/recalculate."""

    recalculated_bytes: int


__all__ = [
    "QuotaResponse",
    "QuotaUpdateRequest",
    "RecalculateResponse",
]
