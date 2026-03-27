"""Pydantic schemas for Skills API endpoints.

Lists user-invocable skills discovered from the skills template directory.
"""

from __future__ import annotations

from pydantic import BaseModel


class SkillResponse(BaseModel):
    """Single skill in the list response."""

    name: str
    description: str
    category: str
    icon: str
    examples: list[str]


class SkillListResponse(BaseModel):
    """Response for GET /api/v1/skills."""

    skills: list[SkillResponse]


__all__ = [
    "SkillListResponse",
    "SkillResponse",
]
