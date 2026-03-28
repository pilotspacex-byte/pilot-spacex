"""SkillGraph SQLAlchemy model.

Workspace-scoped graph representation for a skill template. Stores the
compiled node-edge graph structure used by the graph workflow engine.

Source: Phase 50, P50-02
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat


class SkillGraph(WorkspaceScopedModel):
    """Compiled graph representation for a skill template.

    Each skill template can have one active graph that defines its
    node-edge workflow structure. The graph is compiled from the skill
    content and cached here for execution performance.

    Attributes:
        skill_template_id: FK to the parent skill template.
        graph_json: Full graph structure (nodes, edges, metadata).
        node_count: Number of nodes in the graph.
        edge_count: Number of edges in the graph.
        last_compiled_at: Timestamp of last graph compilation.
    """

    __tablename__ = "skill_graphs"  # type: ignore[assignment]

    skill_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skill_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    graph_json: Mapped[dict] = mapped_column(
        JSONBCompat,
        nullable=False,
    )
    node_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    edge_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    last_compiled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_skill_graphs_skill_template_id",
            "skill_template_id",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<SkillGraph(skill_template_id={self.skill_template_id}, nodes={self.node_count})>"


__all__ = ["SkillGraph"]
