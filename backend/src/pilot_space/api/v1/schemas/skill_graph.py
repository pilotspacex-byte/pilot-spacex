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


class ExecutionTraceStep(BaseModel):
    """A single step in the execution preview trace."""

    node_id: str
    node_type: str
    label: str
    step_number: int
    description: str


class ExecutionPreviewResponse(BaseModel):
    """Response schema for graph execution preview."""

    trace: list[ExecutionTraceStep]


class SkillGraphDecompileRequest(BaseModel):
    """Payload for decompiling SKILL.md content into graph JSON."""

    skill_content: str


class SkillGraphDecompileResponse(BaseModel):
    """Response schema for graph decompilation result."""

    graph_json: dict[str, Any]
    node_count: int
    edge_count: int
    confidence: str


__all__ = [
    "ExecutionPreviewResponse",
    "ExecutionTraceStep",
    "SkillGraphCompileResponse",
    "SkillGraphCreate",
    "SkillGraphDecompileRequest",
    "SkillGraphDecompileResponse",
    "SkillGraphResponse",
    "SkillGraphUpdate",
]
