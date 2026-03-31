"""Pydantic schemas for artifact content read/write endpoints.

Used by the Monaco IDE frontend to load and save code file content.

Feature: Phase 62 — Monaco IDE (IDE-03)
"""

from __future__ import annotations

from pydantic import BaseModel


class ArtifactContentResponse(BaseModel):
    """Response schema for GET /{artifact_id}/content."""

    content: str
    size_bytes: int
    filename: str
    content_type: str


class ArtifactContentUpdateRequest(BaseModel):
    """Request body for PUT /{artifact_id}/content."""

    content: str


__all__ = ["ArtifactContentResponse", "ArtifactContentUpdateRequest"]
