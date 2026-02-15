"""AI Session Management with Redis storage.

Manages multi-turn conversation state for AI agents that support
iterative refinement. Sessions are stored in Redis with 30-minute TTL
and optionally persisted to database for recovery.

T014: SessionManager class with Redis storage
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.exceptions import AIError
from pilot_space.ai.session.session_models import (
    SESSION_KEY_PREFIX,
    SESSION_TTL_SECONDS,
    AIMessage,
    AISession,
    SessionExpiredError,
    SessionNotFoundError,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.cache.redis import RedisClient

logger = get_logger(__name__)


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
    """

    def __init__(self, redis: RedisClient) -> None:
        """Initialize session manager.

        Args:
            redis: Connected Redis client for session storage.
        """
        self._redis = redis

    @staticmethod
    def _session_key(session_id: UUID) -> str:
        """Build Redis key for session."""
        return f"{SESSION_KEY_PREFIX}:{session_id}"

    @staticmethod
    def _user_session_index_key(user_id: UUID, agent_name: str, context_id: UUID | None) -> str:
        """Build Redis key for user session index.

        Used to find active sessions by user/agent/context.
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
            logger.error(
                "failed_to_create_session_in_redis",
                session_id=str(session.id),
            )
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
            "session_created",
            session_id=str(session.id),
            user_id=str(user_id),
            workspace_id=str(workspace_id),
            agent_name=agent_name,
            context_id=str(context_id) if context_id else None,
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
            logger.warning("session_not_found_in_redis", session_id=str(session_id))
            raise SessionNotFoundError(session_id)

        try:
            session = AISession.from_dict(data)
        except (KeyError, ValueError, TypeError) as e:
            # Delete corrupted session from Redis to prevent repeated failures
            logger.warning(
                "deleting_corrupted_session",
                session_id=str(session_id),
                error=str(e),
            )
            await self._redis.delete(session_key)
            raise SessionNotFoundError(session_id) from e

        if session.is_expired():
            logger.warning(
                "session_expired",
                session_id=str(session_id),
                expires_at=session.expires_at.isoformat(),
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

        if message:
            session.messages.append(message)
            session.turn_count += 1

        if context_update:
            session.context.update(context_update)

        if cost_delta > 0:
            session.total_cost_usd += cost_delta

        session.updated_at = datetime.now(UTC)
        session.expires_at = datetime.now(UTC) + timedelta(seconds=SESSION_TTL_SECONDS)

        # Save back to Redis
        session_key = self._session_key(session_id)
        success = await self._redis.set(
            session_key,
            session.to_dict(),
            ttl=SESSION_TTL_SECONDS,
        )

        if not success:
            logger.error(
                "failed_to_update_session_in_redis",
                session_id=str(session_id),
            )
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
            "session_updated",
            session_id=str(session_id),
            turn_count=session.turn_count,
            total_cost_usd=session.total_cost_usd,
        )

        return session

    async def persist_session(self, session: AISession) -> None:
        """Save an already-loaded session back to Redis.

        Use when modifying existing messages (e.g., attaching question_data).

        Args:
            session: Session instance to persist.

        Raises:
            AIError: If Redis write fails.
        """
        session_key = self._session_key(session.id)
        success = await self._redis.set(
            session_key,
            session.to_dict(),
            ttl=SESSION_TTL_SECONDS,
        )
        if not success:
            raise AIError(
                "Failed to persist session",
                details={"session_id": str(session.id)},
            )

    async def end_session(self, session_id: UUID) -> bool:
        """End a session and clean up Redis storage.

        Args:
            session_id: Session UUID to end.

        Returns:
            True if session was deleted, False if it didn't exist.
        """
        try:
            session = await self.get_session(session_id)

            session_key = self._session_key(session_id)
            deleted = await self._redis.delete(session_key)

            index_key = self._user_session_index_key(
                session.user_id,
                session.agent_name,
                session.context_id,
            )
            await self._redis.delete(index_key)

            logger.info(
                "session_ended",
                session_id=str(session_id),
                turn_count=session.turn_count,
                total_cost_usd=session.total_cost_usd,
            )

            return deleted > 0

        except SessionNotFoundError:
            logger.debug("session_not_found_for_cleanup", session_id=str(session_id))
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

        Redis TTL handles most cleanup automatically, but this provides
        explicit cleanup for monitoring.

        Returns:
            Number of sessions cleaned up.
        """
        pattern = f"{SESSION_KEY_PREFIX}:*"
        keys = await self._redis.scan_keys(pattern, max_keys=1000)

        cleaned = 0
        for key in keys:
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
                await self._redis.delete(key)
                cleaned += 1

        if cleaned > 0:
            logger.info("cleaned_up_expired_sessions", cleaned_count=cleaned)

        return cleaned

    async def get_session_metrics(self) -> dict[str, Any]:
        """Get session metrics for monitoring.

        Returns:
            Dictionary with total_sessions, by_agent, total_cost_usd,
            average_age_minutes, and timestamp.
        """
        pattern = f"{SESSION_KEY_PREFIX}:*"
        keys = await self._redis.scan_keys(pattern, max_keys=10000)

        total_sessions = 0
        by_agent: dict[str, int] = {}
        total_cost = 0.0
        session_ages: list[float] = []
        now = datetime.now(UTC)

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
                if session.is_expired():
                    continue

                total_sessions += 1
                agent = session.agent_name
                by_agent[agent] = by_agent.get(agent, 0) + 1
                total_cost += session.total_cost_usd

                age_seconds = (now - session.created_at).total_seconds()
                session_ages.append(age_seconds / 60.0)

            except (KeyError, ValueError, TypeError):
                continue

        avg_age_minutes = sum(session_ages) / len(session_ages) if session_ages else 0.0

        return {
            "total_sessions": total_sessions,
            "by_agent": by_agent,
            "total_cost_usd": round(total_cost, 2),
            "average_age_minutes": round(avg_age_minutes, 2),
            "timestamp": now.isoformat(),
        }


# Re-export models for backward compatibility with existing imports
__all__ = [
    "SESSION_KEY_PREFIX",
    "SESSION_TTL_SECONDS",
    "AIMessage",
    "AISession",
    "SessionExpiredError",
    "SessionManager",
    "SessionNotFoundError",
]
