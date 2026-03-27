"""Pydantic schemas for the related issues API.

Phase 15: RELISS-01..04 — semantic suggestions, manual linking, and dismissal.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class RelatedSuggestion(BaseModel):
    """Semantic suggestion for a related issue."""

    id: UUID
    title: str
    identifier: str
    similarity_score: float
    reason: str


class IssueLinkCreateRequest(BaseModel):
    """Request body for creating an issue relation."""

    target_issue_id: UUID
    link_type: Literal["related"] = "related"


class IssueLinkCreateResponse(BaseModel):
    """Response schema for a newly created issue relation."""

    id: UUID
    source_issue_id: UUID
    target_issue_id: UUID
    link_type: str


__all__ = [
    "IssueLinkCreateRequest",
    "IssueLinkCreateResponse",
    "RelatedSuggestion",
]
