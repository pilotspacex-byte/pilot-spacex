"""Pydantic schemas for skill graph CRUD endpoints.

Source: Phase 52, P52-03
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SkillGraphCreate(BaseModel):
    """Payload for creating a new skill graph."""

    skill_template_id: UUID
    graph_json: dict[str, Any]
    node_count: int = 0
    edge_count: int = 0


class SkillGraphUpdate(BaseModel):
    """Payload for updating an existing skill graph."""

    graph_json: dict[str, Any]
    node_count: int
    edge_count: int


class SkillGraphResponse(BaseModel):
    """Response schema for a skill graph."""

    id: UUID
    workspace_id: UUID
    skill_template_id: UUID
    graph_json: dict[str, Any]
    node_count: int
    edge_count: int
    last_compiled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillGraphCompileResponse(BaseModel):
    """Response schema for graph compilation result."""

    skill_content: str
    node_order: list[str]
    compiled_at: datetime
    graph_id: UUID
    template_id: UUID


__all__ = [
    "SkillGraphCompileResponse",
    "SkillGraphCreate",
    "SkillGraphResponse",
    "SkillGraphUpdate",
]
