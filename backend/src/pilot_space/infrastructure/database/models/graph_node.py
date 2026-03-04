"""GraphNodeModel — SQLAlchemy model for knowledge graph nodes.

Each node represents a typed semantic entity within a workspace
(issue, note, concept, agent, user, project, etc.) and may carry a
1536-dim OpenAI embedding for vector-similarity retrieval.

Nodes are workspace-scoped with RLS enforcement. The optional user_id
column pins a node to a specific workspace member (e.g. per-user agent
memory). Soft delete is inherited from WorkspaceScopedModel.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.graph_edge import GraphEdgeModel


def _make_vector_type(dim: int) -> Any:
    """Return pgvector Vector(dim) or Text fallback for SQLite test environments.

    Args:
        dim: Embedding dimension.

    Returns:
        Vector type for PostgreSQL; Text for all other dialects.
    """
    try:
        from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]

        return Vector(dim)
    except ImportError:
        return Text()


_VECTOR_TYPE: Any = _make_vector_type(768)


class GraphNodeModel(WorkspaceScopedModel):
    """SQLAlchemy ORM model for knowledge graph nodes.

    Columns
    -------
    id            UUID PK, auto-generated.
    workspace_id  FK → workspaces(id) CASCADE DELETE.  RLS boundary.
    user_id       FK → users(id) SET NULL. Optional; scopes node to a member.
    node_type     Discriminator string — one of the permitted node types.
    external_id   UUID of the originating entity (issue_id, note_id, …).
    label         Short human-readable label for display / graph rendering.
    content       Full text content; used for semantic search & summarisation.
    properties    Arbitrary JSONB bag for node-type-specific metadata.
    embedding     vector(768) — 768-dim embedding (Ollama nomic-embed-text / Gemini).
    created_at    Auto-set by server on INSERT (inherited from TimestampMixin).
    updated_at    Auto-set by server on UPDATE (inherited from TimestampMixin).
    is_deleted    Soft-delete flag (inherited from SoftDeleteMixin).
    deleted_at    Timestamp of soft delete (inherited from SoftDeleteMixin).

    Relationships
    -------------
    outgoing_edges  All graph edges where this node is the source.
    incoming_edges  All graph edges where this node is the target.
    """

    __tablename__ = "graph_nodes"  # type: ignore[assignment]

    # Override workspace_id to disable the auto-index from WorkspaceScopedMixin;
    # composite indexes below cover all access patterns more efficiently.
    workspace_id: Mapped[uuid.UUID] = mapped_column(  # type: ignore[assignment]
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=False,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=False,  # partial index defined in __table_args__
    )

    node_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    external_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    label: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )

    properties: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # embedding: vector(768) at DB level (resized by migration 057); Text fallback for SQLite tests.
    # Stored as list[float] in domain; serialised as text in SQLite.
    embedding: Mapped[Any | None] = mapped_column(
        _VECTOR_TYPE,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    outgoing_edges: Mapped[list[GraphEdgeModel]] = relationship(
        "GraphEdgeModel",
        foreign_keys="GraphEdgeModel.source_id",
        back_populates="source_node",
        lazy="select",
    )

    incoming_edges: Mapped[list[GraphEdgeModel]] = relationship(
        "GraphEdgeModel",
        foreign_keys="GraphEdgeModel.target_id",
        back_populates="target_node",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Table-level constraints and indexes
    # ------------------------------------------------------------------

    __table_args__ = (
        # Filtered traversals: workspace x node_type
        Index("ix_graph_nodes_workspace_type", "workspace_id", "node_type"),
        # Recency queries (DESC handled in migration; ORM registers B-tree on column)
        Index("ix_graph_nodes_workspace_created", "workspace_id", "created_at"),
        # Find node by originating entity id
        Index("ix_graph_nodes_workspace_external", "workspace_id", "external_id"),
        # User-scoped nodes (partial — declared in migration, here for ORM awareness)
        Index(
            "ix_graph_nodes_user_id",
            "user_id",
            postgresql_where="user_id IS NOT NULL",
        ),
        # GIN for property queries
        Index(
            "ix_graph_nodes_properties",
            "properties",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return f"<GraphNodeModel(id={self.id}, node_type={self.node_type!r}, label={self.label!r})>"
