"""Session persistence layer bridging Redis and PostgreSQL.

Manages dual storage for AI sessions:
- Redis: Hot storage for active sessions (30min TTL)
- PostgreSQL: Persistent storage for session history and resumption

Reference: T075-T079 (Session Persistence and Resumption)
Design Decisions: DD-058 (Session Management)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.session.session_manager import (
    AIMessage,
    AISession as RedisSession,
    SessionNotFoundError,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.session.session_manager import SessionManager

logger = get_logger(__name__)

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
                "session_store_persisted",
                session_id=str(session_id),
                turn_count=redis_session.turn_count,
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
        # Load from database using raw SQL to avoid ORM selectin-loaded
        # relationships (user, workspace, messages, tasks) which trigger
        # MissingGreenlet errors in async context.
        try:
            from sqlalchemy import text

            row = (
                await self._db.execute(
                    text(
                        "SELECT id, user_id, workspace_id, agent_name, context_id, "
                        "title, session_data, total_cost_usd, turn_count, "
                        "created_at, updated_at, expires_at "
                        "FROM ai_sessions WHERE id = :sid"
                    ),
                    {"sid": session_id},
                )
            ).first()

            if not row:
                logger.warning("Session not found in database: %s", session_id)
                return None

            # Extend TTL if expired (allow resuming historical sessions)
            if row.expires_at < datetime.now(UTC):
                new_expires = datetime.now(UTC) + timedelta(hours=SESSION_TTL_HOURS)
                await self._db.execute(
                    text("UPDATE ai_sessions SET expires_at = :exp WHERE id = :sid"),
                    {"exp": new_expires, "sid": session_id},
                )
                await self._db.flush()
                logger.info("session_store_ttl_extended", session_id=str(session_id))
                expires_at = new_expires
            else:
                expires_at = row.expires_at

            # Parse session_data (comes as dict from JSONB)
            session_data = row.session_data or {}

            # Reconstruct messages
            messages_data = session_data.get("messages", [])
            messages = [AIMessage.from_dict(msg) for msg in messages_data]

            # Create Redis session
            redis_session = RedisSession(
                id=row.id,
                user_id=row.user_id,
                workspace_id=row.workspace_id,
                agent_name=row.agent_name,
                context_id=row.context_id,
                context=session_data.get("context", {}),
                messages=messages,
                total_cost_usd=float(row.total_cost_usd),
                turn_count=row.turn_count,
                created_at=row.created_at,
                updated_at=row.updated_at,
                expires_at=expires_at,
            )

            # Restore to Redis (best-effort, don't fail resume if Redis is down)
            try:
                from pilot_space.ai.session.session_manager import SESSION_TTL_SECONDS

                session_key = self._session_manager._session_key(session_id)  # type: ignore[attr-defined]  # noqa: SLF001
                await self._session_manager._redis.set(  # type: ignore[attr-defined]  # noqa: SLF001
                    session_key,
                    redis_session.to_dict(),
                    ttl=SESSION_TTL_SECONDS,
                )

                index_key = self._session_manager._user_session_index_key(  # type: ignore[attr-defined]  # noqa: SLF001
                    row.user_id,
                    row.agent_name,
                    row.context_id,
                )
                await self._session_manager._redis.set(  # type: ignore[attr-defined]  # noqa: SLF001
                    index_key,
                    str(session_id),
                    ttl=SESSION_TTL_SECONDS,
                )
            except Exception:
                logger.warning("Failed to restore session %s to Redis (non-fatal)", session_id)

            logger.info(
                "session_store_restored",
                session_id=str(session_id),
                turn_count=redis_session.turn_count,
                context_id=str(row.context_id) if row.context_id else None,
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
            from sqlalchemy import text

            logger.info(
                "session_store_load_by_context_searching",
                user_id=str(user_id),
                agent_name=agent_name,
                context_id=str(context_id),
                now=datetime.now(UTC).isoformat(),
            )

            # Use raw SQL to avoid ORM selectin-loaded relationships
            # which trigger MissingGreenlet errors in async context.
            row = (
                await self._db.execute(
                    text(
                        "SELECT id, expires_at FROM ai_sessions "
                        "WHERE user_id = :uid AND agent_name = :aname "
                        "AND context_id = :cid AND expires_at > :now "
                        "ORDER BY updated_at DESC LIMIT 1"
                    ),
                    {
                        "uid": user_id,
                        "aname": agent_name,
                        "cid": context_id,
                        "now": datetime.now(UTC),
                    },
                )
            ).first()

            if not row:
                logger.info(
                    "session_store_load_by_context_not_found",
                    user_id=str(user_id),
                    agent_name=agent_name,
                    context_id=str(context_id),
                )
                return None

            logger.info(
                "session_store_load_by_context_found",
                session_id=str(row.id),
                user_id=str(user_id),
                context_id=str(context_id),
                expires_at=row.expires_at.isoformat(),
            )

            # Reuse load_from_db to restore to Redis
            return await self.load_from_db(row.id)

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
            context_id_str = str(context_id)
            conditions.append(
                or_(
                    DBSession.context_id == context_id,
                    DBSession.session_data["context_history"].cast(String).contains(context_id_str),
                )
            )

        # Search by title or context_history content
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    DBSession.title.ilike(search_pattern),
                    DBSession.session_data["context_history"].cast(String).ilike(search_pattern),
                )
            )

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
                "is_expired": session.expires_at < datetime.now(UTC),
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
            "session_store_deleted",
            session_id=str(session_id),
            redis_deleted=redis_deleted,
            db_deleted=db_deleted,
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
