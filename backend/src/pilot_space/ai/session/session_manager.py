"""AI Session Management with Redis storage.

Manages multi-turn conversation state for AI agents that support
iterative refinement. Sessions are stored in Redis with 30-minute TTL
and optionally persisted to database for recovery.

Features:
- Redis-backed storage with automatic expiration
- User/workspace/agent scoping
- Cost accumulation tracking
- Message history management
- Session recovery from database

T014: SessionManager class with Redis storage
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pilot_space.ai.exceptions import AIError

if TYPE_CHECKING:
    from pilot_space.infrastructure.cache.redis import RedisClient

logger = logging.getLogger(__name__)

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
    """

    role: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    tokens: int | None = None
    cost_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation with ISO timestamps.
        """
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tokens": self.tokens,
            "cost_usd": self.cost_usd,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AIMessage:
        """Create from dictionary.

        Args:
            data: Dictionary with message data.

        Returns:
            AIMessage instance.
        """
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tokens=data.get("tokens"),
            cost_usd=data.get("cost_usd"),
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
        """Convert to dictionary for Redis serialization.

        Returns:
            Dictionary representation with ISO timestamps.
        """
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
        """Create from dictionary.

        Args:
            data: Dictionary with session data.

        Returns:
            AISession instance.
        """
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
        """Check if session has expired.

        Returns:
            True if session has passed its expiration time.
        """
        return datetime.now(UTC) > self.expires_at


class SessionNotFoundError(AIError):
    """Raised when session is not found or has expired."""

    error_code = "session_not_found"
    http_status = 404

    def __init__(self, session_id: UUID) -> None:
        """Initialize session not found error.

        Args:
            session_id: The session ID that was not found.
        """
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
        """Initialize session expired error.

        Args:
            session_id: The expired session ID.
            expired_at: When the session expired.
        """
        super().__init__(
            f"Session {session_id} expired at {expired_at.isoformat()}",
            details={
                "session_id": str(session_id),
                "expired_at": expired_at.isoformat(),
            },
        )
        self.session_id = session_id
        self.expired_at = expired_at


class SessionManager:
    """Manages AI conversation sessions with Redis storage.

    Provides session lifecycle management for multi-turn agent conversations:
    - Create new sessions with initial context
    - Retrieve active sessions
    - Update sessions with new messages and context
    - Clean up expired sessions
    - Persist to database for recovery

    Sessions are stored in Redis with 30-minute TTL and can be
    optionally persisted to database for long-term recovery.

    Example:
        manager = SessionManager(redis_client)

        # Create new session
        session = await manager.create_session(
            user_id=user_id,
            workspace_id=workspace_id,
            agent_name="AIContextAgent",
            context_id=issue_id,
            initial_context={"issue_data": {...}},
        )

        # Update with new message
        await manager.update_session(
            session_id=session.id,
            message=AIMessage(role="user", content="Refine the context"),
            context_update={"additional_info": "..."},
            cost_delta=0.005,
        )

        # Retrieve session
        session = await manager.get_session(session.id)

        # Clean up
        await manager.end_session(session.id)
    """

    def __init__(self, redis: RedisClient) -> None:
        """Initialize session manager.

        Args:
            redis: Connected Redis client for session storage.
        """
        self._redis = redis

    @staticmethod
    def _session_key(session_id: UUID) -> str:
        """Build Redis key for session.

        Args:
            session_id: Session UUID.

        Returns:
            Redis key string.
        """
        return f"{SESSION_KEY_PREFIX}:{session_id}"

    @staticmethod
    def _user_session_index_key(user_id: UUID, agent_name: str, context_id: UUID | None) -> str:
        """Build Redis key for user session index.

        Used to find active sessions by user/agent/context.

        Args:
            user_id: User UUID.
            agent_name: Agent name.
            context_id: Optional context UUID.

        Returns:
            Redis index key string.
        """
        context_part = str(context_id) if context_id else "none"
        return f"{SESSION_KEY_PREFIX}:index:{user_id}:{agent_name}:{context_part}"

    async def create_session(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        agent_name: str,
        context_id: UUID | None = None,
        initial_context: dict[str, Any] | None = None,
    ) -> AISession:
        """Create a new AI session.

        Args:
            user_id: User who owns this session.
            workspace_id: Workspace context.
            agent_name: Name of the agent handling this session.
            context_id: Optional ID of the entity being discussed.
            initial_context: Optional initial context data.

        Returns:
            Created AISession instance.

        Raises:
            AIError: If session creation fails.
            ValueError: If workspace_id is None.
        """
        # Runtime validation - type hints are not enforced at runtime
        if workspace_id is None:  # type: ignore[comparison-overlap]
            raise ValueError("workspace_id is required for session creation")

        session = AISession(
            user_id=user_id,
            workspace_id=workspace_id,
            agent_name=agent_name,
            context_id=context_id,
            context=initial_context or {},
        )

        # Store in Redis
        session_key = self._session_key(session.id)
        success = await self._redis.set(
            session_key,
            session.to_dict(),
            ttl=SESSION_TTL_SECONDS,
        )

        if not success:
            logger.error("Failed to create session in Redis: %s", session.id)
            raise AIError(
                "Failed to create session",
                details={"session_id": str(session.id)},
            )

        # Create index for session lookup
        index_key = self._user_session_index_key(user_id, agent_name, context_id)
        await self._redis.set(
            index_key,
            str(session.id),
            ttl=SESSION_TTL_SECONDS,
        )

        logger.info(
            "Created AI session",
            extra={
                "session_id": str(session.id),
                "user_id": str(user_id),
                "workspace_id": str(workspace_id),
                "agent_name": agent_name,
                "context_id": str(context_id) if context_id else None,
            },
        )

        return session

    async def get_session(self, session_id: UUID) -> AISession:
        """Retrieve a session by ID.

        Args:
            session_id: Session UUID.

        Returns:
            AISession instance.

        Raises:
            SessionNotFoundError: If session doesn't exist or has been deleted.
            SessionExpiredError: If session exists but has expired.
        """
        session_key = self._session_key(session_id)
        data = await self._redis.get(session_key)

        if data is None:
            logger.warning("Session not found in Redis: %s", session_id)
            raise SessionNotFoundError(session_id)

        try:
            session = AISession.from_dict(data)
        except (KeyError, ValueError, TypeError) as e:
            # Delete corrupted session from Redis to prevent repeated failures
            logger.warning(
                "Deleting corrupted session %s from Redis: %s",
                session_id,
                str(e),
            )
            await self._redis.delete(session_key)
            raise SessionNotFoundError(session_id) from e

        if session.is_expired():
            logger.warning(
                "Session %s has expired at %s",
                session_id,
                session.expires_at.isoformat(),
            )
            raise SessionExpiredError(session_id, session.expires_at)

        return session

    async def update_session(
        self,
        session_id: UUID,
        *,
        message: AIMessage | None = None,
        context_update: dict[str, Any] | None = None,
        cost_delta: float = 0.0,
    ) -> AISession:
        """Update an existing session.

        Args:
            session_id: Session UUID.
            message: Optional new message to append to history.
            context_update: Optional context updates to merge.
            cost_delta: Optional cost to add to total.

        Returns:
            Updated AISession instance.

        Raises:
            SessionNotFoundError: If session doesn't exist.
            SessionExpiredError: If session has expired.
        """
        session = await self.get_session(session_id)

        # Apply updates (mutate in-place)
        if message:
            session.messages.append(message)
            session.turn_count += 1

        if context_update:
            session.context.update(context_update)

        if cost_delta > 0:
            session.total_cost_usd += cost_delta

        session.updated_at = datetime.now(UTC)

        # Extend expiration
        session.expires_at = datetime.now(UTC) + timedelta(seconds=SESSION_TTL_SECONDS)

        # Save back to Redis
        session_key = self._session_key(session_id)
        success = await self._redis.set(
            session_key,
            session.to_dict(),
            ttl=SESSION_TTL_SECONDS,
        )

        if not success:
            logger.error("Failed to update session in Redis: %s", session_id)
            raise AIError(
                "Failed to update session",
                details={"session_id": str(session_id)},
            )

        # Refresh index TTL
        index_key = self._user_session_index_key(
            session.user_id,
            session.agent_name,
            session.context_id,
        )
        await self._redis.expire(index_key, SESSION_TTL_SECONDS)

        logger.debug(
            "Updated AI session",
            extra={
                "session_id": str(session_id),
                "turn_count": session.turn_count,
                "total_cost_usd": session.total_cost_usd,
            },
        )

        return session

    async def end_session(self, session_id: UUID) -> bool:
        """End a session and clean up Redis storage.

        Args:
            session_id: Session UUID to end.

        Returns:
            True if session was deleted, False if it didn't exist.
        """
        try:
            session = await self.get_session(session_id)

            # Delete session key
            session_key = self._session_key(session_id)
            deleted = await self._redis.delete(session_key)

            # Delete index key
            index_key = self._user_session_index_key(
                session.user_id,
                session.agent_name,
                session.context_id,
            )
            await self._redis.delete(index_key)

            logger.info(
                "Ended AI session",
                extra={
                    "session_id": str(session_id),
                    "turn_count": session.turn_count,
                    "total_cost_usd": session.total_cost_usd,
                },
            )

            return deleted > 0

        except SessionNotFoundError:
            logger.debug("Session not found for cleanup: %s", session_id)
            return False

    async def get_active_session(
        self,
        user_id: UUID,
        agent_name: str,
        context_id: UUID | None = None,
    ) -> AISession | None:
        """Find an active session for user/agent/context.

        Args:
            user_id: User UUID.
            agent_name: Agent name.
            context_id: Optional context UUID.

        Returns:
            Active AISession if found, None otherwise.
        """
        index_key = self._user_session_index_key(user_id, agent_name, context_id)
        session_id_str = await self._redis.get(index_key)

        if session_id_str is None:
            return None

        try:
            session_id = UUID(session_id_str)
            return await self.get_session(session_id)
        except (ValueError, SessionNotFoundError, SessionExpiredError):
            # Index exists but session is gone or invalid - clean up index
            await self._redis.delete(index_key)
            return None

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from Redis.

        This is a maintenance operation that scans for expired sessions
        and removes them. Redis TTL handles most cleanup automatically,
        but this provides explicit cleanup for monitoring.

        Returns:
            Number of sessions cleaned up.
        """
        pattern = f"{SESSION_KEY_PREFIX}:*"
        keys = await self._redis.scan_keys(pattern, max_keys=1000)

        cleaned = 0
        for key in keys:
            # Skip index keys
            if ":index:" in key:
                continue

            data = await self._redis.get(key)
            if data is None:
                continue

            try:
                session = AISession.from_dict(data)
                if session.is_expired():
                    await self._redis.delete(key)
                    cleaned += 1
            except (KeyError, ValueError, TypeError):
                # Invalid session data - delete it
                await self._redis.delete(key)
                cleaned += 1

        if cleaned > 0:
            logger.info("Cleaned up %d expired sessions", cleaned)

        return cleaned

    async def get_session_metrics(self) -> dict[str, Any]:
        """Get session metrics for monitoring (T331).

        Provides real-time metrics about active sessions:
        - Total session count
        - Sessions grouped by agent name
        - Average session age
        - Total cost across all sessions

        Returns:
            Dictionary with session metrics.

        Example:
            >>> metrics = await session_manager.get_session_metrics()
            >>> print(f"Total sessions: {metrics['total_sessions']}")
            >>> print(f"By agent: {metrics['by_agent']}")
        """
        pattern = f"{SESSION_KEY_PREFIX}:*"
        keys = await self._redis.scan_keys(pattern, max_keys=10000)

        total_sessions = 0
        by_agent: dict[str, int] = {}
        total_cost = 0.0
        session_ages: list[float] = []
        now = datetime.now(UTC)

        # Filter out index keys before batch fetch
        session_keys = [k for k in keys if ":index:" not in k]

        if not session_keys:
            return {
                "total_sessions": 0,
                "by_agent": {},
                "total_cost_usd": 0.0,
                "average_age_minutes": 0.0,
                "timestamp": now.isoformat(),
            }

        # Batch fetch all session data in one round-trip
        all_data = await self._redis.mget(*session_keys)

        for data in all_data:
            if data is None:
                continue

            try:
                session = AISession.from_dict(data)

                # Skip expired sessions
                if session.is_expired():
                    continue

                total_sessions += 1

                # Count by agent
                agent = session.agent_name
                by_agent[agent] = by_agent.get(agent, 0) + 1

                # Accumulate cost
                total_cost += session.total_cost_usd

                # Calculate age in minutes
                age_seconds = (now - session.created_at).total_seconds()
                session_ages.append(age_seconds / 60.0)

            except (KeyError, ValueError, TypeError):
                # Skip invalid session data
                continue

        # Calculate average age
        avg_age_minutes = sum(session_ages) / len(session_ages) if session_ages else 0.0

        return {
            "total_sessions": total_sessions,
            "by_agent": by_agent,
            "total_cost_usd": round(total_cost, 2),
            "average_age_minutes": round(avg_age_minutes, 2),
            "timestamp": now.isoformat(),
        }


__all__ = [
    "SESSION_KEY_PREFIX",
    "SESSION_TTL_SECONDS",
    "AIMessage",
    "AISession",
    "SessionExpiredError",
    "SessionManager",
    "SessionNotFoundError",
]
