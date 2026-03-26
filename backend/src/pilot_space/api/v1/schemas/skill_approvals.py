"""Pydantic schemas for Skill Approval API endpoints (T-046).

Approve or reject pending skill executions.

Approval expires after 24 hours (T-070 pg_cron job).
Admin approval required for destructive skills (C-7).

Feature 015: AI Workforce Platform — Sprint 2
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class SkillApproveRequest(BaseModel):
    """Request body for approving a skill execution.

    Attributes:
        note_id: Note UUID to write the approved output to.
        output_override: Optional user-edited output. If None, original skill output is used.
    """

    note_id: UUID | None = None
    output_override: dict[str, object] | None = None


class SkillApprovalResponse(BaseModel):
    """Response for skill approval or rejection.

    Attributes:
        execution_id: UUID of the resolved execution.
        status: Final approval status ('approved' or 'rejected').
    """

    execution_id: UUID
    status: str


class PendingSkillExecutionItem(BaseModel):
    """Single pending skill execution in the list response.

    Attributes:
        execution_id: UUID of the execution awaiting approval.
        skill_name: Name of the skill that produced this output.
        intent_id: Parent work intent UUID.
        required_approval_role: Role required to approve (None = any member).
        created_at: When the execution record was created.
    """

    execution_id: UUID = Field(description="SkillExecution UUID")
    skill_name: str = Field(description="Skill that produced the pending output")
    intent_id: UUID = Field(description="Parent WorkIntent UUID")
    required_approval_role: str | None = Field(
        default=None,
        description="Minimum role required to approve (None = any member)",
    )
    created_at: str = Field(description="ISO 8601 creation timestamp")


class PendingApprovalsResponse(BaseModel):
    """Paginated list of pending skill executions.

    Attributes:
        items: Pending executions on this page.
        total: Total number of pending executions in the workspace.
        limit: Page size used.
        offset: Page offset used.
    """

    items: list[PendingSkillExecutionItem] = Field(description="Pending executions")
    total: int = Field(description="Total pending count")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Page offset")


__all__ = [
    "PendingApprovalsResponse",
    "PendingSkillExecutionItem",
    "SkillApprovalResponse",
    "SkillApproveRequest",
]
