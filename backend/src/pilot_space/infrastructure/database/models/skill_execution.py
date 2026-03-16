"""SkillExecution SQLAlchemy model.

Records SDK subagent executions with approval workflow support.
Feature 015: AI Workforce Platform (C-1, C-7)
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import BaseModel
from pilot_space.infrastructure.database.types import JSONBCompat

from .work_intent import WorkIntent


class SkillApprovalStatus(StrEnum):
    """Approval lifecycle for a skill execution."""

    AUTO_APPROVED = "auto_approved"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class SkillApprovalRole(StrEnum):
    """Minimum workspace role required to approve (C-7)."""

    ADMIN = "admin"
    MEMBER = "member"


class SkillExecution(BaseModel):
    """SQLAlchemy model for skill execution audit records.

    Tracks each SDK subagent execution with approval state.
    RLS enforced via join to work_intents.workspace_id.
    """

    __tablename__ = "skill_executions"  # type: ignore[assignment]

    # Parent intent
    intent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("work_intents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Which skill ran
    skill_name: Mapped[str] = mapped_column(Text, nullable=False)

    # Approval workflow
    approval_status: Mapped[SkillApprovalStatus] = mapped_column(
        SQLEnum(
            SkillApprovalStatus,
            name="skill_approval_status_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SkillApprovalStatus.AUTO_APPROVED,
    )

    # C-7: role-based approval (None = no role restriction)
    required_approval_role: Mapped[SkillApprovalRole | None] = mapped_column(
        SQLEnum(
            SkillApprovalRole,
            name="skill_approval_role_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
    )

    # Execution output
    output: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=None,
    )

    # Relationship back to intent
    intent: Mapped[WorkIntent] = relationship(
        "WorkIntent",
        lazy="joined",
    )

    __table_args__ = (
        Index("ix_skill_executions_intent_id", "intent_id"),
        Index("ix_skill_executions_approval_status", "approval_status"),
        Index("ix_skill_executions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<SkillExecution(id={self.id}, skill={self.skill_name!r}, "
            f"status={self.approval_status})>"
        )
