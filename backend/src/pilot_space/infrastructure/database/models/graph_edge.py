"""GraphEdgeModel — SQLAlchemy model for knowledge graph edges.

An edge is a directed, typed relationship between two graph nodes.
workspace_id is denormalised from the source node so that RLS policies
can filter on a single column without a cross-table join, keeping edge
queries O(1) at the policy evaluation layer.

Edges do NOT inherit WorkspaceScopedModel because they are not first-class
workspace entities; they are connective tissue between nodes. BaseModel
is intentionally skipped for the same reason — edges have no soft-delete
semantics (they are removed when either endpoint node is deleted via CASCADE).
The table has its own UUID PK, created_at, and workspace_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import Base
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.database.types import JSONBCompat


class GraphEdgeModel(Base):
    """SQLAlchemy ORM model for knowledge graph edges.

    Columns
    -------
    id            UUID PK, auto-generated.
    source_id     FK → graph_nodes(id) CASCADE DELETE.
    target_id     FK → graph_nodes(id) CASCADE DELETE.
    workspace_id  FK → workspaces(id) CASCADE DELETE.  RLS boundary.
    edge_type     Discriminator string — permitted edge types.
    properties    Arbitrary JSONB bag for edge metadata.
    weight        Relationship strength in [0.0, 1.0]. Default 0.5.
    created_at    Auto-set by server on INSERT.

    Constraints
    -----------
    - source_id != target_id  (no self-loops)
    - UNIQUE (source_id, target_id, edge_type)  (no duplicate typed edges)

    Relationships
    -------------
    source_node  The originating GraphNodeModel.
    target_node  The destination GraphNodeModel.
    """

    __tablename__ = "graph_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )

    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    edge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    properties: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        server_default="0.5",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    source_node: Mapped[GraphNodeModel] = relationship(
        "GraphNodeModel",
        foreign_keys=[source_id],
        back_populates="outgoing_edges",
        lazy="select",
    )

    target_node: Mapped[GraphNodeModel] = relationship(
        "GraphNodeModel",
        foreign_keys=[target_id],
        back_populates="incoming_edges",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Table-level indexes
    # ------------------------------------------------------------------

    __table_args__ = (
        # Outgoing edge traversal
        Index("ix_graph_edges_source_id", "source_id"),
        # Incoming edge traversal
        Index("ix_graph_edges_target_id", "target_id"),
        # Filtered edge lookups by workspace and type
        Index("ix_graph_edges_workspace_type", "workspace_id", "edge_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<GraphEdgeModel(id={self.id}, edge_type={self.edge_type!r}, "
            f"source_id={self.source_id}, target_id={self.target_id})>"
        )
