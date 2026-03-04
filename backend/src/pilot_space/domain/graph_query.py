"""GraphQuery value objects for the knowledge graph system.

Defines the query contract for hybrid search (vector + full-text + recency)
and the result containers for scored node sets and graph context.

Feature 016: Knowledge Graph — Memory Engine replacement
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from pilot_space.domain.graph_edge import GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType

_DEFAULT_LIMIT = 10
_DEFAULT_MAX_DEPTH = 2


@dataclass(frozen=True)
class GraphQuery:
    """Value object encapsulating a hybrid knowledge graph search request.

    Supports filtering by node type and user scope. When node_types is
    None all node types are included. When include_user_context is True
    and user_id is provided, user-scoped nodes (preferences, patterns)
    are surfaced alongside workspace nodes.

    Attributes:
        query_text: Natural language search string.
        workspace_id: Scope search to this workspace.
        user_id: Optional user scope for personal nodes.
        node_types: Restrict to these node types (None = all).
        limit: Maximum number of scored nodes to return.
        max_depth: Graph traversal depth for edge resolution.
        include_user_context: Surface user-scoped nodes when True.
    """

    query_text: str
    workspace_id: UUID
    user_id: UUID | None = None
    node_types: list[NodeType] | None = None
    limit: int = _DEFAULT_LIMIT
    max_depth: int = _DEFAULT_MAX_DEPTH
    include_user_context: bool = True


@dataclass
class ScoredNode:
    """A ranked node from a hybrid knowledge graph search.

    The combined score is the authoritative ranking signal. Component
    scores (embedding, text, recency, edge_density) are preserved for
    debugging and score-fusion experiments.

    Attributes:
        node: The matched GraphNode.
        score: Combined ranking score [0.0, 1.0].
        embedding_score: Cosine similarity score [0.0, 1.0].
        text_score: Full-text relevance score [0.0, 1.0].
        recency_score: Time-decay score [0.0, 1.0].
        edge_density_score: Connectivity score [0.0, 1.0].
    """

    node: GraphNode
    score: float
    embedding_score: float
    text_score: float
    recency_score: float
    edge_density_score: float


@dataclass
class GraphContext:
    """Result container for a knowledge graph search.

    Bundles the ranked node list with the intra-result edges so callers
    can reconstruct the local sub-graph without additional queries.

    Attributes:
        nodes: Ranked list of matched nodes (highest score first).
        edges: Edges between the returned nodes (intra-result graph).
        query: The originating query (for audit / caching).
        embedding_used: True when vector search contributed to ranking.
    """

    nodes: list[ScoredNode]
    edges: list[GraphEdge]
    query: GraphQuery
    embedding_used: bool = False
    _node_ids: set[UUID] = field(default_factory=set, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Build node-id index for fast edge filtering."""
        self._node_ids = {sn.node.id for sn in self.nodes}

    @property
    def top_node(self) -> ScoredNode | None:
        """Return the highest-ranked node, or None if result is empty."""
        return self.nodes[0] if self.nodes else None

    @property
    def node_count(self) -> int:
        """Total number of scored nodes in the result."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Total number of intra-result edges."""
        return len(self.edges)

    def intra_edges(self) -> list[GraphEdge]:
        """Return edges where both endpoints appear in the result set.

        This is a convenience re-filter for callers who receive a
        GraphContext that may contain edges to nodes outside the result.

        Returns:
            Subset of self.edges with both endpoints in self.nodes.
        """
        return [
            e for e in self.edges if e.source_id in self._node_ids and e.target_id in self._node_ids
        ]


__all__ = ["GraphContext", "GraphQuery", "ScoredNode"]
