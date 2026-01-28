"""AISession SQLAlchemy model.

Stores multi-turn AI conversation sessions for agents that support
iterative refinement (AIContextAgent, ConversationAgent).

References:
- T009: Create ai_sessions migration
- specs/004-mvp-agents-build/tasks/P2-T006-T010.md
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import Base, WorkspaceScopedMixin
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.ai_message import AIMessage
    from pilot_space.infrastructure.database.models.ai_task import AITask
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class AISession(Base, WorkspaceScopedMixin):
    """Multi-turn AI conversation session.

    Stores conversation state for agents that support iterative refinement.
    Sessions expire after 30 minutes of inactivity.

    Attributes:
        workspace_id: Reference to parent workspace.
        user_id: User who owns the session.
        agent_name: Type of agent (ai_context, conversation).
        context_id: Optional reference to context (issue_id, note_id).
        session_data: Conversation history and state in JSON format.
        total_cost_usd: Accumulated cost for this session.
        turn_count: Number of conversation turns.
        expires_at: When this session expires.
    """

    __tablename__ = "ai_sessions"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "agent_name", "context_id", name="uq_ai_sessions_user_agent_context"
        ),
        Index("ix_ai_sessions_expires_at", "expires_at"),
        Index("ix_ai_sessions_user_agent", "user_id", "agent_name"),
        Index("ix_ai_sessions_workspace_id", "workspace_id"),
        {"schema": None},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # User who owns the session
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Agent type
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Type of agent (ai_context, conversation)",
    )

    # Optional context reference
    context_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Optional reference to context (issue_id, note_id)",
    )

    # Session state
    session_data: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
        doc="Conversation history, context, and state",
    )

    # Cost tracking
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        server_default="0",
        nullable=False,
        doc="Accumulated cost for this session",
    )

    turn_count: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
        nullable=False,
        doc="Number of conversation turns",
    )

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When this session expires (default: 30 minutes from last activity)",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        back_populates="ai_sessions",
        lazy="selectin",
    )

    user: Mapped[User] = relationship(
        "User",
        lazy="selectin",
    )

    messages: Mapped[list[AIMessage]] = relationship(
        "AIMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    tasks: Mapped[list[AITask]] = relationship(
        "AITask",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<AISession(id={self.id}, user_id={self.user_id}, "
            f"agent={self.agent_name}, turns={self.turn_count})>"
        )
