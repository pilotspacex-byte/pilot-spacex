"""AIApprovalRequest SQLAlchemy model.

Stores human-in-the-loop approval requests for AI actions (DD-003).
Critical actions require explicit user approval before execution.

References:
- T007: Create ai_approval_requests migration
- specs/004-mvp-agents-build/tasks/P2-T006-T010.md
- specs/005-conversational-agent-arch/data-model.md
- docs/DESIGN_DECISIONS.md#DD-003
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import Base, WorkspaceScopedMixin

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.ai_message import AIMessage
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class ApprovalStatus(StrEnum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    MODIFIED = "modified"


class AIApprovalRequest(Base, WorkspaceScopedMixin):
    """Human-in-the-loop approval request for AI actions.

    Implements approval flow per DD-003. Critical actions (delete, merge)
    require explicit approval. Requests expire after 24 hours.

    Attributes:
        workspace_id: Reference to parent workspace.
        message_id: Reference to message that triggered approval (Wave 2).
        user_id: User who triggered the AI action.
        agent_name: Name of the agent requesting approval.
        action_type: Type of action (create_issue, merge_pr, etc.).
        description: Human-readable action description.
        consequences: Impact description for reviewer.
        affected_entities: List of entities that will be modified.
        urgency: Urgency level (low, medium, high).
        payload: Action-specific data in JSON format.
        context: Optional context for the reviewer.
        proposed_content: Original AI proposal (for approve-with-modifications).
        modified_content: User modifications (for modified status).
        status: Current status (pending, approved, rejected, expired, modified).
        expires_at: When this request expires.
        resolved_at: When the request was resolved.
        resolved_by: User who resolved the request.
        resolution_note: Optional note from the resolver.
    """

    __tablename__ = "ai_approval_requests"
    __table_args__ = (
        Index("ix_ai_approval_requests_workspace_status", "workspace_id", "status"),
        Index("ix_ai_approval_requests_user_id", "user_id"),
        {"schema": None},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )

    # Message reference (Wave 2)
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_messages.id", ondelete="CASCADE"),
        nullable=True,
        doc="Reference to message that triggered approval (Wave 2)",
    )

    # User who triggered the action
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Agent information
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Name of the agent requesting approval (e.g., issue_extractor)",
    )

    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Type of action (e.g., create_issue, merge_pr, delete_issue)",
    )

    # Action description and impact
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Human-readable action description",
    )

    consequences: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Impact description for reviewer",
    )

    affected_entities: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="List of entities that will be modified [{type, id, name}]",
    )

    urgency: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
        doc="Urgency level (low, medium, high)",
    )

    # Action payload
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        doc="Action-specific data (issue content, PR details, etc.)",
    )

    context: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Optional context for the reviewer (related entities, history)",
    )

    # Approve-with-modifications support
    proposed_content: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Original AI proposal (for approve-with-modifications flow)",
    )

    modified_content: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="User modifications (for modified status)",
    )

    # Status
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(
            ApprovalStatus,
            name="approval_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ApprovalStatus.PENDING,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When this request expires (default: 24 hours)",
    )

    # Resolution
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    resolution_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional note from the resolver",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        back_populates="approval_requests",
        lazy="selectin",
    )

    message: Mapped[AIMessage | None] = relationship(
        "AIMessage",
        back_populates="approval_requests",
        lazy="selectin",
    )

    user: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    resolver: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[resolved_by],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<AIApprovalRequest(id={self.id}, agent={self.agent_name}, "
            f"action={self.action_type}, status={self.status})>"
        )
