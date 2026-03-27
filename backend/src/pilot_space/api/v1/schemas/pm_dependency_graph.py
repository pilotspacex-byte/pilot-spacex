"""Pydantic schemas for PM Block dependency graph endpoints.

T-237: Dependency graph (nodes + edges + circular detection)

Feature 017: Note Versioning / PM Block Engine — Phase 2c
"""

from __future__ import annotations

from pydantic import BaseModel


class DepMapNode(BaseModel):
    """A single node in the dependency map DAG."""

    id: str
    identifier: str
    name: str
    state: str
    state_group: str


class DepMapEdge(BaseModel):
    """A directed edge between two nodes in the dependency map."""

    source_id: str
    target_id: str
    is_critical: bool = False


class DependencyMapResponse(BaseModel):
    """Response for the dependency map endpoint (T-237)."""

    nodes: list[DepMapNode]
    edges: list[DepMapEdge]
    critical_path: list[str]
    circular_deps: list[list[str]]
    has_circular: bool


__all__ = [
    "DepMapEdge",
    "DepMapNode",
    "DependencyMapResponse",
]
