"""AIToolCall SQLAlchemy model.

Records tool invocations during AI processing, including SDK tools
and MCP tools. Tracks execution status and results.

References:
- T009: Create ai_tool_calls table
- specs/005-conversational-agent-arch/data-model.md
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import Base
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.ai_message import AIMessage


class ToolCallStatus(StrEnum):
    """Status of a tool invocation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AIToolCall(Base):
    """Tool invocation within a message.

    Records execution of SDK tools (Skill, Task, etc.) and MCP tools
    (pilotspace_search, get_issue_by_id, etc.) during AI processing.

    Attributes:
        message_id: Reference to parent message.
        tool_name: SDK tool or MCP tool name.
        tool_input: Tool arguments as JSON.
        tool_output: Tool result as JSON (null if failed).
        status: Execution status (pending, running, completed, failed, cancelled).
        error_message: Error message if failed.
        started_at: When execution started.
        completed_at: When execution completed.
    """

    __tablename__ = "ai_tool_calls"
    __table_args__ = (
        Index("ix_ai_tool_calls_message_id", "message_id"),
        Index(
            "ix_ai_tool_calls_status_pending",
            "status",
            postgresql_where="status IN ('pending', 'running')",
        ),
        {"schema": None},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )

    # Message reference
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_messages.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Tool information
    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="SDK tool or MCP tool name (e.g., 'Skill', 'Read', 'pilotspace_search')",
    )

    tool_input: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
        doc="Tool arguments as JSON",
    )

    tool_output: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        doc="Tool result as JSON (null if failed)",
    )

    # Status tracking
    status: Mapped[ToolCallStatus] = mapped_column(
        String(20),
        default=ToolCallStatus.PENDING,
        nullable=False,
        doc="Execution status",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if execution failed",
    )

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When execution started",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When execution completed or failed",
    )

    # Relationships
    message: Mapped[AIMessage] = relationship(
        "AIMessage",
        back_populates="tool_calls",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<AIToolCall(id={self.id}, tool={self.tool_name}, status={self.status})>"
