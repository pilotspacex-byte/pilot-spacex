"""Pydantic schemas for project-scoped dependency graph endpoints.

T-237: GET /api/v1/projects/{project_id}/dependency-graph
       Returns nodes, edges, critical_path, and circular dependency detection.

Feature 017: Note Versioning / PM Block Engine — Phase 2c
"""

from __future__ import annotations

from pydantic import BaseModel


class DependencyNode(BaseModel):
    """A single node in the project dependency graph."""

    id: str
    identifier: str
    name: str
    state: str
    state_group: str


class DependencyEdge(BaseModel):
    """A directed edge between two nodes in the project dependency graph."""

    source_id: str
    target_id: str
    is_critical: bool = False


class DependencyGraphResponse(BaseModel):
    """Response for the project dependency graph endpoint."""

    nodes: list[DependencyNode]
    edges: list[DependencyEdge]
    critical_path: list[str]
    circular_deps: list[list[str]]
    has_circular: bool


__all__ = [
    "DependencyEdge",
    "DependencyGraphResponse",
    "DependencyNode",
]
