"""AI Cost Record SQLAlchemy model.

Tracks AI usage costs per request for billing and budget tracking.

T013: Create CostRecord model for AI cost tracking.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class AICostRecord(WorkspaceScopedModel):
    """AI cost record for tracking usage and spending.

    Tracks costs per AI request for:
    - Budget monitoring
    - Cost reporting and analytics
    - Per-workspace and per-user cost summaries
    - Cost anomaly detection

    Attributes:
        user_id: FK to user who initiated the request.
        agent_name: Name of the agent that processed the request.
        provider: LLM provider (anthropic, openai, google).
        model: Specific model used (e.g., claude-sonnet-4-20250514).
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.
        cost_usd: Calculated cost in USD with 6 decimal precision.
    """

    __tablename__ = "ai_cost_records"  # type: ignore[assignment]

    # User who initiated the request
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Agent that processed the request
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # LLM provider and model
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Token counts
    input_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Cost in USD with micro-precision (6 decimals for sub-cent accuracy)
    cost_usd: Mapped[float] = mapped_column(
        Numeric(10, 6),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        lazy="joined",
    )
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        back_populates="cost_records",
        lazy="joined",
    )

    # Indexes for efficient queries
    # Note: workspace_id index is automatically created by WorkspaceScopedMixin
    __table_args__ = (
        Index("ix_ai_cost_records_user_id", "user_id"),
        Index("ix_ai_cost_records_agent_name", "agent_name"),
        Index("ix_ai_cost_records_provider", "provider"),
        Index("ix_ai_cost_records_created_at", "created_at"),
        # Composite indexes for summary queries
        Index(
            "ix_ai_cost_records_workspace_created",
            "workspace_id",
            "created_at",
        ),
        Index(
            "ix_ai_cost_records_user_created",
            "user_id",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<AICostRecord(id={self.id}, provider={self.provider}, cost=${self.cost_usd:.6f})>"

    @property
    def total_tokens(self) -> int:
        """Get total token count (input + output)."""
        return self.input_tokens + self.output_tokens
