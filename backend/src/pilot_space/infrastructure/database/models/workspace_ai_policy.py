"""WorkspaceAIPolicy SQLAlchemy model.

Per-role x per-action-type AI approval policy for Phase 4 AI Governance (AIGOV-01).

Absence of a row means fall back to hardcoded defaults in ApprovalService.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel


class WorkspaceAIPolicy(WorkspaceScopedModel):
    """Per-role x per-action-type AI approval policy.

    Configurable per workspace, per role, per action_type. Absence of a row
    means fall back to the hardcoded ApprovalLevel threshold defaults (DD-003).

    Attributes:
        workspace_id: FK to workspaces (from WorkspaceScopedModel).
        role: Workspace role this policy applies to (e.g. 'OWNER', 'ADMIN', 'MEMBER').
        action_type: Action type string (e.g. 'create_issues', 'delete_issue').
        requires_approval: True = always require human approval; False = auto-execute.
    """

    __tablename__ = "workspace_ai_policy"  # type: ignore[assignment]

    role: Mapped[str] = mapped_column(String(20), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "role",
            "action_type",
            name="uq_workspace_ai_policy_workspace_role_action",
        ),
        Index("ix_workspace_ai_policy_workspace_role", "workspace_id", "role"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<WorkspaceAIPolicy("
            f"workspace_id={self.workspace_id}, "
            f"role={self.role}, "
            f"action_type={self.action_type}, "
            f"requires_approval={self.requires_approval}"
            f")>"
        )
