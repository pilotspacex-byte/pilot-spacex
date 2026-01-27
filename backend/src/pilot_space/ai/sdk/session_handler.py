"""Session handler for multi-turn Claude Agent SDK conversations.

Manages conversation state across multiple requests, handling:
- Message history persistence (Redis)
- Token budget management (8000 token limit)
- Session lifecycle (30 minute TTL)
- Context window optimization

Reference: docs/architect/claude-agent-sdk-architecture.md
Design Decisions: DD-058 (SDK mode for streaming)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from pilot_space.ai.session.session_manager import SessionManager


@dataclass
class ConversationMessage:
    """Single message in a conversation.

    Attributes:
        role: Message role (user, assistant, system)
        content: Message content (text or structured blocks)
        timestamp: When message was created
        tokens: Estimated token count
        metadata: Additional metadata (cost, model, etc.)
    """

    role: str
    content: str | list[dict[str, Any]]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_sdk_format(self) -> dict[str, Any]:
        """Convert to Claude Agent SDK message format."""
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass
class ConversationSession:
    """Multi-turn conversation session.

    Attributes:
        session_id: Unique session identifier
        workspace_id: Workspace UUID for RLS
        user_id: User UUID for attribution
        agent_name: Agent this session belongs to
        messages: Conversation message history
        created_at: Session creation time
        updated_at: Last update time
        total_tokens: Cumulative token count
        total_cost_usd: Cumulative cost in USD
        metadata: Additional session metadata
    """

    session_id: UUID
    workspace_id: UUID
    user_id: UUID
    agent_name: str
    messages: list[ConversationMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if session has exceeded TTL (30 minutes)."""
        ttl = timedelta(minutes=30)
        return datetime.now(UTC) - self.updated_at > ttl

    def add_message(self, message: ConversationMessage) -> None:
        """Add message to session history.

        Updates total_tokens and updated_at timestamp.
        """
        self.messages.append(message)
        self.total_tokens += message.tokens
        self.updated_at = datetime.now(UTC)

    def get_messages_for_sdk(self, max_tokens: int = 8000) -> list[dict[str, Any]]:
        """Get messages in SDK format, respecting token budget.

        Implements sliding window: keeps most recent messages that fit
        within max_tokens limit. Always includes system message if present.

        Args:
            max_tokens: Maximum tokens to include (default: 8000)

        Returns:
            List of messages in Claude Agent SDK format
        """
        if not self.messages:
            return []

        # Separate system messages from conversation
        system_messages = [m for m in self.messages if m.role == "system"]
        conversation_messages = [m for m in self.messages if m.role != "system"]

        # Calculate system message tokens
        system_tokens = sum(m.tokens for m in system_messages)
        remaining_budget = max_tokens - system_tokens

        # Add messages from most recent, staying within budget
        included_messages: list[ConversationMessage] = []
        current_tokens = 0

        for message in reversed(conversation_messages):
            if current_tokens + message.tokens > remaining_budget:
                break
            included_messages.insert(0, message)
            current_tokens += message.tokens

        # Combine system + conversation messages
        all_messages = system_messages + included_messages
        return [m.to_sdk_format() for m in all_messages]


class SessionHandler:
    """Handler for managing Claude Agent SDK conversation sessions.

    Responsibilities:
    - Create and retrieve sessions
    - Persist session state to Redis
    - Enforce token budgets and TTL
    - Optimize context windows

    Usage:
        handler = SessionHandler(session_manager)
        session = await handler.create_session(workspace_id, user_id, "ai_context")
        messages = session.get_messages_for_sdk(max_tokens=8000)
    """

    def __init__(self, session_manager: SessionManager):
        """Initialize handler with session manager.

        Args:
            session_manager: SessionManager for Redis persistence
        """
        self._session_manager = session_manager

    # Note: The following methods are placeholders pending SessionManager interface finalization
    # The existing SessionManager uses AISession, not ConversationSession
    # These methods provide the interface for the SDK integration layer

    async def create_session(
        self,
        workspace_id: UUID,
        user_id: UUID,
        agent_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationSession:
        """Create new conversation session.

        Note: This is a placeholder. Implementation will use SessionManager.create()
        once interface is finalized to bridge AISession <-> ConversationSession.
        """
        return ConversationSession(
            session_id=uuid4(),
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name=agent_name,
            metadata=metadata or {},
        )
        # Actual implementation will create AISession via SessionManager.create()

    async def get_session(self, _session_id: UUID) -> ConversationSession | None:
        """Retrieve existing session by ID.

        Note: This is a placeholder. Will use SessionManager.get() to retrieve
        AISession and convert to ConversationSession.
        """
        # Actual implementation will fetch AISession and convert
        return None

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str | list[dict[str, Any]],
        tokens: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add message to session.

        Note: This is a placeholder. Will use SessionManager.add_message().
        """
        # Actual implementation will add message to AISession

    async def update_cost(
        self,
        session_id: UUID,
        cost_usd: float,
    ) -> None:
        """Update session cost.

        Note: This is a placeholder. Will update AISession cost.
        """
        # Actual implementation will update AISession

    async def delete_session(self, _session_id: UUID) -> bool:
        """Delete session.

        Note: This is a placeholder. Will use SessionManager.delete().
        """
        # Actual implementation will delete AISession
        return False
