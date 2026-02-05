"""Session persistence layer bridging Redis and PostgreSQL.

Manages dual storage for AI sessions:
- Redis: Hot storage for active sessions (30min TTL)
- PostgreSQL: Persistent storage for session history and resumption

Reference: T075-T079 (Session Persistence and Resumption)
Design Decisions: DD-058 (Session Management)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.session.session_manager import (
    AIMessage,
    AISession as RedisSession,
    SessionNotFoundError,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.session.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Session configuration
SESSION_TTL_HOURS = 24  # Database persistence TTL


class SessionStore:
    """Dual-storage session manager for Redis and PostgreSQL.

    Provides session persistence and resumption capabilities:
    - Save active sessions to database on message_stop
    - Load sessions from database when resuming
    - List user sessions across workspaces
    - Clean up expired sessions

    Example:
        store = SessionStore(session_manager, db_session)

        # Save session to database
        await store.save_to_db(session_id)

        # Resume from database
        session = await store.load_from_db(session_id)

        # List user sessions
        sessions = await store.list_sessions_for_user(user_id, workspace_id)
    """

    def __init__(
        self,
        session_manager: SessionManager,
        db_session: AsyncSession,
    ) -> None:
        """Initialize session store.

        Args:
            session_manager: Redis-backed session manager.
            db_session: PostgreSQL database session.
        """
        self._session_manager = session_manager
        self._db = db_session

    async def save_to_db(self, session_id: UUID) -> bool:
        """Save Redis session to PostgreSQL for persistence.

        Called on message_stop events to persist conversation history.

        Args:
            session_id: Session UUID to save.

        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            # Get from Redis
            redis_session = await self._session_manager.get_session(session_id)

            # Check if already exists in DB by session_id
            from sqlalchemy import select

            from pilot_space.infrastructure.database.models.ai_session import (
                AISession as DBSession,
            )

            stmt = select(DBSession).where(DBSession.id == session_id)
            result = await self._db.execute(stmt)
            db_session = result.scalar_one_or_none()

            # NOTE: Context-based fallback removed in multi-context session architecture.
            # Each "New Chat" creates a distinct session, not bound to a single context.
            # Sessions now track context_history in session_data for multi-context support.

            # Convert messages to JSON-serializable format
            messages_data = [msg.to_dict() for msg in redis_session.messages]

            # Generate title from first user message if not set
            title = None
            if redis_session.messages:
                first_user_msg = next(
                    (m for m in redis_session.messages if m.role == "user"),
                    None,
                )
                if first_user_msg:
                    # Truncate at 50 chars, add ellipsis if needed
                    title = first_user_msg.content[:50].strip()
                    if len(first_user_msg.content) > 50:
                        title += "..."

            # Prepare session data with context_history for multi-context support
            session_data = {
                "messages": messages_data,
                "context": redis_session.context,
                "context_history": redis_session.context.get("context_history", []),
                "turn_count": redis_session.turn_count,
            }

            if db_session:
                # Update existing
                from decimal import Decimal

                db_session.session_data = session_data
                db_session.total_cost_usd = Decimal(str(redis_session.total_cost_usd))
                db_session.turn_count = redis_session.turn_count
                db_session.expires_at = datetime.now(UTC) + timedelta(hours=SESSION_TTL_HOURS)
                # Update title if not already set
                if title and not db_session.title:
                    db_session.title = title
            else:
                # Create new
                from decimal import Decimal

                db_session = DBSession(
                    id=redis_session.id,
                    workspace_id=redis_session.workspace_id,
                    user_id=redis_session.user_id,
                    agent_name=redis_session.agent_name,
                    context_id=redis_session.context_id,
                    title=title,
                    session_data=session_data,
                    total_cost_usd=Decimal(str(redis_session.total_cost_usd)),
                    turn_count=redis_session.turn_count,
                    expires_at=datetime.now(UTC) + timedelta(hours=SESSION_TTL_HOURS),
                )
                self._db.add(db_session)

            await self._db.commit()

            logger.info(
                "Persisted session to database",
                extra={
                    "session_id": str(session_id),
                    "turn_count": redis_session.turn_count,
                },
            )

            return True

        except SessionNotFoundError:
            logger.warning("Session not found in Redis: %s", session_id)
            return False
        except Exception:
            logger.exception("Failed to persist session %s to database", session_id)
            await self._db.rollback()
            return False

    async def load_from_db(self, session_id: UUID) -> RedisSession | None:
        """Load session from PostgreSQL and restore to Redis.

        Called when resuming a session that may have expired from Redis.

        Args:
            session_id: Session UUID to load.

        Returns:
            Loaded RedisSession or None if not found.
        """
        try:
            # Try Redis first
            try:
                redis_session = await self._session_manager.get_session(session_id)
                logger.debug("Session found in Redis: %s", session_id)

                # Ensure context index exists (may have expired separately)
                if redis_session.context_id is not None:
                    from pilot_space.ai.session.session_manager import SESSION_TTL_SECONDS

                    index_key = self._session_manager._user_session_index_key(  # type: ignore[attr-defined]  # noqa: SLF001
                        redis_session.user_id,
                        redis_session.agent_name,
                        redis_session.context_id,
                    )
                    await self._session_manager._redis.set(  # type: ignore[attr-defined]  # noqa: SLF001
                        index_key,
                        str(session_id),
                        ttl=SESSION_TTL_SECONDS,
                    )

                return redis_session
            except SessionNotFoundError:
                pass

            # Load from database
            from sqlalchemy import select

            from pilot_space.infrastructure.database.models.ai_session import (
                AISession as DBSession,
            )

            stmt = select(DBSession).where(DBSession.id == session_id)
            result = await self._db.execute(stmt)
            db_session = result.scalar_one_or_none()

            if not db_session:
                logger.warning("Session not found in database: %s", session_id)
                return None

            # Check expiration
            if db_session.expires_at < datetime.now(UTC):
                logger.warning("Session expired in database: %s", session_id)
                return None

            # Reconstruct messages
            messages_data = db_session.session_data.get("messages", [])
            messages = [AIMessage.from_dict(msg) for msg in messages_data]

            # Create Redis session
            redis_session = RedisSession(
                id=db_session.id,
                user_id=db_session.user_id,
                workspace_id=db_session.workspace_id,
                agent_name=db_session.agent_name,
                context_id=db_session.context_id,
                context=db_session.session_data.get("context", {}),
                messages=messages,
                total_cost_usd=float(db_session.total_cost_usd),
                turn_count=db_session.turn_count,
                created_at=db_session.created_at,
                updated_at=db_session.updated_at,
                expires_at=db_session.expires_at,
            )

            # Restore to Redis via public interface
            from pilot_space.ai.session.session_manager import SESSION_TTL_SECONDS

            # Use internal methods with type ignore for private access
            session_key = self._session_manager._session_key(session_id)  # type: ignore[attr-defined]  # noqa: SLF001
            await self._session_manager._redis.set(  # type: ignore[attr-defined]  # noqa: SLF001
                session_key,
                redis_session.to_dict(),
                ttl=SESSION_TTL_SECONDS,
            )

            # Restore context index for session lookup
            index_key = self._session_manager._user_session_index_key(  # type: ignore[attr-defined]  # noqa: SLF001
                db_session.user_id,
                db_session.agent_name,
                db_session.context_id,
            )
            await self._session_manager._redis.set(  # type: ignore[attr-defined]  # noqa: SLF001
                index_key,
                str(session_id),
                ttl=SESSION_TTL_SECONDS,
            )

            logger.info(
                "Restored session from database to Redis (with index)",
                extra={
                    "session_id": str(session_id),
                    "turn_count": redis_session.turn_count,
                    "context_id": str(db_session.context_id) if db_session.context_id else None,
                },
            )

            return redis_session

        except Exception:
            logger.exception("Failed to load session %s from database", session_id)
            return None

    async def load_by_context(
        self,
        user_id: UUID,
        agent_name: str,
        context_id: UUID,
    ) -> RedisSession | None:
        """Find most recent active session by context from PostgreSQL.

        Called when Redis index has expired but session may still exist
        in PostgreSQL (24h TTL). Restores found session to Redis.

        Args:
            user_id: User UUID.
            agent_name: Agent name.
            context_id: Context entity UUID (note_id, issue_id, etc).

        Returns:
            RedisSession if found and not expired, None otherwise.
        """
        try:
            from sqlalchemy import and_, desc, select

            from pilot_space.infrastructure.database.models.ai_session import (
                AISession as DBSession,
            )

            logger.info(
                "load_by_context: searching for session",
                extra={
                    "user_id": str(user_id),
                    "agent_name": agent_name,
                    "context_id": str(context_id),
                    "now": datetime.now(UTC).isoformat(),
                },
            )

            stmt = (
                select(DBSession)
                .where(
                    and_(
                        DBSession.user_id == user_id,
                        DBSession.agent_name == agent_name,
                        DBSession.context_id == context_id,
                        DBSession.expires_at > datetime.now(UTC),
                    )
                )
                .order_by(desc(DBSession.updated_at))
                .limit(1)
            )

            result = await self._db.execute(stmt)
            db_session = result.scalar_one_or_none()

            if not db_session:
                logger.info(
                    "load_by_context: no session found in DB",
                    extra={
                        "user_id": str(user_id),
                        "agent_name": agent_name,
                        "context_id": str(context_id),
                    },
                )
                return None

            logger.info(
                "load_by_context: found session in DB, restoring to Redis",
                extra={
                    "session_id": str(db_session.id),
                    "user_id": str(user_id),
                    "context_id": str(context_id),
                    "expires_at": db_session.expires_at.isoformat(),
                },
            )

            # Reuse load_from_db to restore to Redis
            return await self.load_from_db(db_session.id)

        except Exception:
            logger.exception(
                "Failed to load session by context %s from database",
                context_id,
            )
            return None

    async def list_sessions_for_user(
        self,
        user_id: UUID,
        workspace_id: UUID | None = None,
        agent_name: str | None = None,
        context_id: UUID | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List sessions for a user.

        Args:
            user_id: User UUID.
            workspace_id: Optional workspace filter.
            agent_name: Optional agent filter.
            context_id: Optional context entity filter (note_id, issue_id).
            search: Optional search query (matches title and context_history).
            limit: Maximum sessions to return (default: 50).

        Returns:
            List of session metadata dictionaries with title and context_history.
        """
        from sqlalchemy import String, and_, desc, or_, select

        from pilot_space.infrastructure.database.models.ai_session import (
            AISession as DBSession,
        )

        # Build query
        conditions = [DBSession.user_id == user_id]

        if workspace_id:
            conditions.append(DBSession.workspace_id == workspace_id)

        if agent_name:
            conditions.append(DBSession.agent_name == agent_name)

        if context_id:
            conditions.append(DBSession.context_id == context_id)

        # Search by title or context_history content
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    DBSession.title.ilike(search_pattern),
                    DBSession.session_data["context_history"].cast(String).ilike(search_pattern),
                )
            )

        # Filter out expired sessions
        conditions.append(DBSession.expires_at > datetime.now(UTC))

        stmt = (
            select(DBSession)
            .where(and_(*conditions))
            .order_by(desc(DBSession.updated_at))
            .limit(limit)
        )

        result = await self._db.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": str(session.id),
                "workspace_id": str(session.workspace_id),
                "agent_name": session.agent_name,
                "context_id": str(session.context_id) if session.context_id else None,
                "title": session.title,
                "context_history": session.session_data.get("context_history", []),
                "turn_count": session.turn_count,
                "total_cost_usd": float(session.total_cost_usd),
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
            }
            for session in sessions
        ]

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete session from both Redis and database.

        Args:
            session_id: Session UUID to delete.

        Returns:
            True if deleted from either storage, False if not found.
        """
        redis_deleted = await self._session_manager.end_session(session_id)

        from sqlalchemy import delete

        from pilot_space.infrastructure.database.models.ai_session import (
            AISession as DBSession,
        )

        stmt = delete(DBSession).where(DBSession.id == session_id)
        result = await self._db.execute(stmt)
        await self._db.commit()

        db_deleted = (result.rowcount or 0) > 0  # type: ignore[attr-defined]

        logger.info(
            "Deleted session",
            extra={
                "session_id": str(session_id),
                "redis_deleted": redis_deleted,
                "db_deleted": db_deleted,
            },
        )

        return redis_deleted or db_deleted

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from database.

        Redis handles its own TTL-based cleanup.

        Returns:
            Number of sessions cleaned up.
        """
        from sqlalchemy import delete

        from pilot_space.infrastructure.database.models.ai_session import (
            AISession as DBSession,
        )

        stmt = delete(DBSession).where(DBSession.expires_at < datetime.now(UTC))
        result = await self._db.execute(stmt)
        await self._db.commit()

        count = result.rowcount or 0  # type: ignore[attr-defined]

        if count > 0:
            logger.info("Cleaned up %d expired sessions from database", count)

        return count


__all__ = ["SessionStore"]
