"""GraphEdge domain entity for the knowledge graph system.

Represents a directed edge (relationship) between two GraphNode vertices.
Edges encode semantic relationships between workspace entities.

Feature 016: Knowledge Graph — Memory Engine replacement
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

_WEIGHT_MIN = 0.0
_WEIGHT_MAX = 1.0
_WEIGHT_DEFAULT = 0.5


class EdgeType(StrEnum):
    """Semantic relationship type for a graph edge."""

    RELATES_TO = "relates_to"
    CAUSED_BY = "caused_by"
    LED_TO = "led_to"
    DECIDED_IN = "decided_in"
    AUTHORED_BY = "authored_by"
    ASSIGNED_TO = "assigned_to"
    BELONGS_TO = "belongs_to"
    REFERENCES = "references"
    LEARNED_FROM = "learned_from"
    SUMMARIZES = "summarizes"
    BLOCKS = "blocks"
    DUPLICATES = "duplicates"
    PARENT_OF = "parent_of"


@dataclass
class GraphEdge:
    """Domain entity representing a directed edge in the knowledge graph.

    Edges are directed (source -> target) and carry a weight that
    represents relationship strength or confidence. Self-loops are
    explicitly forbidden as they have no semantic meaning.

    Attributes:
        source_id: UUID of the source GraphNode.
        target_id: UUID of the target GraphNode.
        edge_type: Semantic relationship type.
        id: Unique identifier for this edge.
        properties: Optional JSONB metadata for this relationship.
        weight: Relationship strength [0.0, 1.0]; default 0.5.
        created_at: UTC creation timestamp.
    """

    source_id: UUID
    target_id: UUID
    edge_type: EdgeType
    id: UUID = field(default_factory=uuid4)
    properties: dict[str, object] = field(default_factory=dict)
    weight: float = _WEIGHT_DEFAULT
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __post_init__(self) -> None:
        """Validate edge invariants after construction."""
        if not (_WEIGHT_MIN <= self.weight <= _WEIGHT_MAX):
            msg = f"Edge weight must be between {_WEIGHT_MIN} and {_WEIGHT_MAX}, got {self.weight}"
            raise ValueError(msg)
        if self.source_id == self.target_id:
            msg = f"Self-loop edges are not allowed: source_id == target_id == {self.source_id}"
            raise ValueError(msg)


__all__ = ["EdgeType", "GraphEdge"]
