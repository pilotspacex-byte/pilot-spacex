"""AuditLog SQLAlchemy model for compliance and audit trail.

Provides an immutable, workspace-scoped audit log for all user, system, and AI actions.
Intentionally does NOT inherit SoftDeleteMixin — audit records must be immutable.

Requirements: AUDIT-01, AUDIT-02
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import (
    Base,
    TimestampMixin,
    WorkspaceScopedMixin,
)
from pilot_space.infrastructure.database.types import JSONBCompat


class ActorType(str, Enum):
    """Type of actor that performed an audited action.

    USER: A human workspace member.
    SYSTEM: An automated system action (e.g., pg_cron, migrations).
    AI: An AI agent action (e.g., PilotSpaceAgent skill execution).
    """

    USER = "USER"
    SYSTEM = "SYSTEM"
    AI = "AI"


class AuditLog(Base, TimestampMixin, WorkspaceScopedMixin):
    """Immutable audit log entry for compliance record-keeping.

    Records every significant action taken within a workspace by any actor type.
    This model deliberately avoids SoftDeleteMixin — rows are immutable and can only
    be purged by the pg_cron retention job via the fn_audit_log_immutable bypass.

    Attributes:
        id: UUID primary key.
        workspace_id: FK to workspace (from WorkspaceScopedMixin).
        created_at: Timestamp of the action (from TimestampMixin).
        updated_at: Last updated (from TimestampMixin — always == created_at due to trigger).
        actor_id: UUID of the user who performed the action. NULL for system-only actions.
        actor_type: Enum indicating USER, SYSTEM, or AI actor.
        action: Dot-notation action string e.g. "issue.create", "member.role_changed".
        resource_type: Resource category e.g. "issue", "note", "cycle", "member".
        resource_id: UUID of the affected resource. NULL for workspace-level actions.
        payload: JSONB diff {"before": {}, "after": {}} of changed fields.
        ai_input: Raw AI input (prompt/context). Only set when actor_type=AI.
        ai_output: Raw AI output. Only set when actor_type=AI.
        ai_model: Model identifier used e.g. "claude-sonnet-4-20250514".
        ai_token_cost: Token count consumed. Only set when actor_type=AI.
        ai_rationale: AI's stated rationale for the action.
        ip_address: Client IP address from X-Forwarded-For header.
    """

    __tablename__ = "audit_log"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default="gen_random_uuid()",
    )

    # Actor information
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    actor_type: Mapped[ActorType] = mapped_column(
        String(10),
        nullable=False,
    )

    # Action description
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Payload diff: {"before": {field: value}, "after": {field: value}}
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
    )

    # AI-specific fields (only populated when actor_type=AI)
    ai_input: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
    )
    ai_output: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
    )
    ai_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    ai_token_cost: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    ai_rationale: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Request context
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6-safe: max 45 chars
        nullable=True,
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        # Primary query pattern: list audit log for a workspace sorted by time
        Index("ix_audit_log_workspace_created", "workspace_id", "created_at"),
        # Filter by actor within a workspace
        Index("ix_audit_log_workspace_actor", "workspace_id", "actor_id"),
        # Filter by action within a workspace
        Index("ix_audit_log_workspace_action", "workspace_id", "action"),
        # Filter by resource_type within a workspace
        Index("ix_audit_log_workspace_resource_type", "workspace_id", "resource_type"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<AuditLog(id={self.id}, action={self.action}, actor_type={self.actor_type})>"
