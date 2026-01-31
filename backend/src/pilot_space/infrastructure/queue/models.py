"""Queue data models and types.

Contains queue-related dataclasses, enums, and type definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class QueueName(StrEnum):
    """Predefined queue names for Pilot Space.

    Queue naming convention:
    - ai_* : AI-related processing tasks
    - Integration queues: Named after the integration (github, slack, etc.)
    - System queues: Core platform operations (notifications, etc.)
    """

    # AI Processing Queues (Priority levels)
    AI_HIGH = "ai_high"  # PR review, critical AI context (5 min timeout)
    AI_NORMAL = "ai_normal"  # Embedding generation, duplicate detection
    AI_LOW = "ai_low"  # Knowledge graph recalculation

    # Conversational AI (10-min visibility timeout)
    AI_CHAT = "ai_chat"

    # Legacy alias
    AI_TASKS = "ai_tasks"

    # Integration Queues
    GITHUB_WEBHOOKS = "github_webhooks"

    # System Queues
    NOTIFICATIONS = "notifications"

    # Dead Letter Queue
    DEAD_LETTER = "dead_letter"


class MessageStatus(StrEnum):
    """Queue message status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


def parse_datetime(value: str | datetime | None) -> datetime:
    """Parse datetime from string or return default.

    Args:
        value: ISO format datetime string, datetime object, or None.

    Returns:
        Parsed datetime or current UTC time if parsing fails.
    """
    if value is None:
        return datetime.now(tz=UTC)
    if isinstance(value, datetime):
        return value
    try:
        # Handle ISO format with or without timezone
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except (ValueError, AttributeError):
        return datetime.now(tz=UTC)


@dataclass
class QueueMessage:
    """Queue message with metadata.

    Attributes:
        id: Unique message identifier.
        queue_name: Name of the queue.
        payload: JSON-serializable message payload.
        status: Current message status.
        attempts: Number of processing attempts.
        max_attempts: Maximum retry attempts before dead-lettering.
        created_at: Message creation timestamp.
        processed_at: Last processing attempt timestamp.
        error: Last error message if failed.
        visibility_timeout: Seconds until message becomes visible again.
    """

    id: str
    queue_name: str
    payload: dict[str, Any]
    status: MessageStatus = MessageStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    processed_at: datetime | None = None
    error: str | None = None
    visibility_timeout: int = 30

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueueMessage:
        """Create QueueMessage from dictionary (RPC response)."""
        return cls(
            id=str(data.get("msg_id", data.get("id", ""))),
            queue_name=data.get("queue_name", ""),
            payload=data.get("message", data.get("payload", {})),
            status=MessageStatus(data.get("status", "pending")),
            attempts=data.get("read_ct", data.get("attempts", 0)),
            max_attempts=data.get("max_attempts", 3),
            created_at=parse_datetime(data.get("enqueued_at", data.get("created_at"))),
            processed_at=parse_datetime(data.get("processed_at")),
            error=data.get("error"),
            visibility_timeout=data.get("vt", data.get("visibility_timeout", 30)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "queue_name": self.queue_name,
            "payload": self.payload,
            "status": self.status.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error": self.error,
            "visibility_timeout": self.visibility_timeout,
        }
