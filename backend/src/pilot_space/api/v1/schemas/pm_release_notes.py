"""Pydantic schemas for PM Block release notes endpoints.

T-244: Release notes generation from completed issues

Feature 017: Note Versioning / PM Block Engine — Phase 2e
"""

from __future__ import annotations

from pydantic import BaseModel


class ReleaseEntry(BaseModel):
    """A single issue entry in the release notes."""

    issue_id: str
    identifier: str
    name: str
    category: str  # features / bug_fixes / improvements / internal / uncategorized
    confidence: float
    human_edited: bool = False


class ReleaseNotesResponse(BaseModel):
    """Response for the release notes endpoint (T-244)."""

    cycle_id: str
    version_label: str
    entries: list[ReleaseEntry]
    generated_at: str


__all__ = [
    "ReleaseEntry",
    "ReleaseNotesResponse",
]
