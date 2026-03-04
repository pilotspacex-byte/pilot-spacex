"""Pydantic v2 schemas for the Knowledge Graph API.

Feature 016: Knowledge Graph — Unit 7 REST API
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GraphNodeDTO(BaseModel):
    """A single knowledge graph node for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Node UUID as string")
    node_type: str = Field(description="NodeType enum value (e.g. 'issue', 'note')")
    label: str = Field(description="Human-readable display name")
    summary: str | None = Field(default=None, description="First 120 chars of content")
    properties: dict[str, Any] = Field(default_factory=dict, description="Type-specific metadata")
    created_at: datetime = Field(description="UTC creation timestamp")
    updated_at: datetime = Field(description="UTC last-modified timestamp")
    score: float | None = Field(default=None, description="Relevance score (search results only)")


class GraphEdgeDTO(BaseModel):
    """A directed relationship between two graph nodes."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Edge UUID as string")
    source_id: str = Field(description="Source node UUID")
    target_id: str = Field(description="Target node UUID")
    edge_type: str = Field(description="EdgeType enum value (e.g. 'relates_to')")
    label: str = Field(description="Human-readable edge label (same as edge_type)")
    weight: float = Field(description="Relationship strength [0.0, 1.0]")
    properties: dict[str, Any] = Field(default_factory=dict, description="Edge metadata")


class GraphResponse(BaseModel):
    """Graph subgraph response containing nodes and connecting edges."""

    model_config = ConfigDict(from_attributes=True)

    nodes: list[GraphNodeDTO] = Field(default_factory=list, description="Graph nodes")
    edges: list[GraphEdgeDTO] = Field(default_factory=list, description="Edges between the nodes")
    center_node_id: UUID | None = Field(
        default=None,
        description="UUID of the focal node (search pivot or root)",
    )


__all__ = [
    "GraphEdgeDTO",
    "GraphNodeDTO",
    "GraphResponse",
]
