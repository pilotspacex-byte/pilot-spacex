"""AI Session data models and error classes.

Defines the core data structures for AI session management:
- AIMessage: Single message in a conversation
- AISession: Multi-turn conversation session state
- Session error types for not-found and expired states

These models are used by SessionManager for Redis serialization
and by SDK components for session state access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pilot_space.ai.exceptions import AIError

# Session configuration constants
SESSION_TTL_SECONDS = 1800  # 30 minutes
SESSION_KEY_PREFIX = "ai_session"


@dataclass(frozen=True, slots=True, kw_only=True)
class AIMessage:
    """Single message in an AI conversation.

    Attributes:
        role: Message role (user, assistant, system).
        content: Message text content.
        timestamp: When the message was created.
        tokens: Optional token count for this message.
        cost_usd: Optional cost for this message.
        question_data: Optional Q&A data for session resume rendering.
            Contains list of {questionId, questions, answers} when an assistant
            message asked questions and the user answered them.
            Supports both legacy single-dict format and new list format.
        tool_calls: Optional list of tool call records for session resume.
            Each entry: {id, name, input, output, status, error_message, duration_ms}.
    """

    role: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    tokens: int | None = None
    cost_usd: float | None = None
    question_data: list[dict[str, Any]] | dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tokens": self.tokens,
            "cost_usd": self.cost_usd,
        }
        if self.question_data is not None:
            result["question_data"] = self.question_data
        if self.tool_calls is not None:
            result["tool_calls"] = self.tool_calls
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AIMessage:
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tokens=data.get("tokens"),
            cost_usd=data.get("cost_usd"),
            question_data=data.get("question_data"),
            tool_calls=data.get("tool_calls"),
        )


@dataclass(slots=True, kw_only=True)
class AISession:
    """Multi-turn AI conversation session.

    Tracks conversation state across multiple turns for agents that
    support iterative refinement (e.g., AIContextAgent).

    Attributes:
        id: Unique session identifier.
        user_id: User who owns this session.
        workspace_id: Workspace context for this session.
        agent_name: Name of the agent handling this session.
        context_id: Optional ID of the initial context (e.g., issue_id).
        title: Auto-generated title from first user message.
        context: Session context data (user preferences, entity data, etc.).
        messages: Conversation message history.
        total_cost_usd: Accumulated cost across all turns.
        turn_count: Number of turns in this session.
        created_at: When the session was created.
        updated_at: Last modification time.
        expires_at: When the session expires.
    """

    id: UUID = field(default_factory=uuid4)
    user_id: UUID
    workspace_id: UUID
    agent_name: str
    context_id: UUID | None = None
    title: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    messages: list[AIMessage] = field(default_factory=list)
    total_cost_usd: float = 0.0
    turn_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(UTC) + timedelta(seconds=SESSION_TTL_SECONDS)
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Redis serialization."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "workspace_id": str(self.workspace_id),
            "agent_name": self.agent_name,
            "context_id": str(self.context_id) if self.context_id else None,
            "title": self.title,
            "context": self.context,
            "messages": [msg.to_dict() for msg in self.messages],
            "total_cost_usd": self.total_cost_usd,
            "turn_count": self.turn_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AISession:
        """Create from dictionary."""
        messages = [AIMessage.from_dict(msg) for msg in data.get("messages", [])]
        return cls(
            id=UUID(data["id"]),
            user_id=UUID(data["user_id"]),
            workspace_id=UUID(data["workspace_id"]),
            agent_name=data["agent_name"],
            context_id=UUID(data["context_id"]) if data.get("context_id") else None,
            title=data.get("title"),
            context=data.get("context", {}),
            messages=messages,
            total_cost_usd=data.get("total_cost_usd", 0.0),
            turn_count=data.get("turn_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
        )

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now(UTC) > self.expires_at


class SessionNotFoundError(AIError):
    """Raised when session is not found or has expired."""

    error_code = "session_not_found"
    http_status = 404

    def __init__(self, session_id: UUID) -> None:
        super().__init__(
            f"Session {session_id} not found or has expired",
            details={"session_id": str(session_id)},
        )
        self.session_id = session_id


class SessionExpiredError(AIError):
    """Raised when attempting to use an expired session."""

    error_code = "session_expired"
    http_status = 410

    def __init__(self, session_id: UUID, expired_at: datetime) -> None:
        super().__init__(
            f"Session {session_id} expired at {expired_at.isoformat()}",
            details={
                "session_id": str(session_id),
                "expired_at": expired_at.isoformat(),
            },
        )
        self.session_id = session_id
        self.expired_at = expired_at


__all__ = [
    "SESSION_KEY_PREFIX",
    "SESSION_TTL_SECONDS",
    "AIMessage",
    "AISession",
    "SessionExpiredError",
    "SessionNotFoundError",
]
