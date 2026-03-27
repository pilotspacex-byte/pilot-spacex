"""Pydantic schemas for AI governance API endpoints.

Covers policy matrix CRUD, BYOK status.

Requirements: AIGOV-01, AIGOV-02, AIGOV-04, AIGOV-05
"""

from __future__ import annotations

from pydantic import BaseModel


class PolicyRowIn(BaseModel):
    """Request body for policy upsert."""

    requires_approval: bool


class PolicyRowResponse(BaseModel):
    """Response for a single policy row."""

    role: str
    action_type: str
    requires_approval: bool


class AIStatusResponse(BaseModel):
    """Response for BYOK status endpoint."""

    byok_configured: bool
    providers: list[str]


__all__ = ["AIStatusResponse", "PolicyRowIn", "PolicyRowResponse"]
