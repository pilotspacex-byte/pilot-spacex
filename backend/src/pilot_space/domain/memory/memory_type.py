"""MemoryType — high-level discriminator over the GraphNode substrate.

Phase 69 (AI Memory + Granular Tool Permissions) introduces a typed
memory layer on top of the existing knowledge graph. Rather than shipping
a new table, we reuse ``graph_nodes`` and map memory types onto
``NodeType`` values. Some memory types map to pre-existing node types
(e.g. NOTE_SUMMARY → NOTE_CHUNK) while others map to new node types added
in migration 106 (AGENT_TURN, USER_CORRECTION, PR_REVIEW_FINDING).

See ``.planning/phases/69-ai-memory-and-granular-tool-permissions/``.
"""

from __future__ import annotations

from enum import StrEnum

from pilot_space.domain.graph_node import NodeType


class MemoryType(StrEnum):
    """High-level memory discriminator used by recall / lifecycle services.

    Values are stable and are serialized into pgmq payloads as the
    ``memory_type`` discriminator understood by the kg_populate handler.
    """

    NOTE_SUMMARY = "note_summary"
    ISSUE_DECISION = "issue_decision"
    AGENT_TURN = "agent_turn"
    USER_CORRECTION = "user_correction"
    PR_REVIEW_FINDING = "pr_review_finding"

    def to_node_type(self) -> NodeType:
        """Return the underlying GraphNode NodeType for this memory type."""
        return MEMORY_TYPE_TO_NODE_TYPE[self]


MEMORY_TYPE_TO_NODE_TYPE: dict[MemoryType, NodeType] = {
    MemoryType.NOTE_SUMMARY: NodeType.NOTE_CHUNK,
    MemoryType.ISSUE_DECISION: NodeType.DECISION,
    MemoryType.AGENT_TURN: NodeType.AGENT_TURN,
    MemoryType.USER_CORRECTION: NodeType.USER_CORRECTION,
    MemoryType.PR_REVIEW_FINDING: NodeType.PR_REVIEW_FINDING,
}


__all__ = ["MEMORY_TYPE_TO_NODE_TYPE", "MemoryType"]
