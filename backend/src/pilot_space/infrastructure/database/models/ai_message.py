"""AIMessage SQLAlchemy model.

Stores individual messages in a multi-turn conversation session.
Messages include user inputs, assistant responses, and system prompts.

References:
- T008: Create ai_messages table
- specs/005-conversational-agent-arch/data-model.md
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import Base

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.ai_approval_request import (
        AIApprovalRequest,
    )
    from pilot_space.infrastructure.database.models.ai_session import AISession
    from pilot_space.infrastructure.database.models.ai_tool_call import AIToolCall


class MessageRole(StrEnum):
    """Role of a message in the conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AIMessage(Base):
    """Single message in a conversation session.

    Stores user inputs, assistant responses, and system prompts with metadata.
    Messages are ordered by created_at within a session.

    Attributes:
        session_id: Reference to parent session.
        role: Message role (user, assistant, or system).
        content: Message text content (may include markdown).
        message_metadata: Optional metadata (skill, agent, tokens, model).
        created_at: When the message was created.
    """

    __tablename__ = "ai_messages"
    __table_args__ = (
        Index("ix_ai_messages_session_id", "session_id"),
        Index("ix_ai_messages_session_created", "session_id", "created_at"),
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

    # Session reference
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Message content
    role: Mapped[MessageRole] = mapped_column(
        String(20),
        nullable=False,
        doc="Message role (user, assistant, or system)",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Message text content (may include markdown)",
    )

    # Message metadata (skill, agent, tokens, model)
    message_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",  # Column name in DB
        JSONB,
        nullable=True,
        doc="Skill/agent info, token usage, model used",
    )
    # message_metadata structure:
    # {
    #   "skill": "extract-issues",
    #   "agent": "pilotspace",
    #   "tokens": {"input": 120, "output": 350},
    #   "model": "claude-sonnet-4-20250514",
    #   "confidence": "RECOMMENDED"
    # }

    # Relationships
    session: Mapped[AISession] = relationship(
        "AISession",
        back_populates="messages",
        lazy="selectin",
    )

    tool_calls: Mapped[list[AIToolCall]] = relationship(
        "AIToolCall",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    approval_requests: Mapped[list[AIApprovalRequest]] = relationship(
        "AIApprovalRequest",
        back_populates="message",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<AIMessage(id={self.id}, role={self.role}, content='{content_preview}')>"
