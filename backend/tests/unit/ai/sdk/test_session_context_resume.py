"""Unit tests for session resumption by context_id.

Tests the fix for sessions always being recreated instead of resumed
when users return to the same note/issue. Covers:
- SessionHandler.create_session with context_id
- SessionHandler.get_session_by_context (Redis + PostgreSQL fallback)
- SessionStore.load_by_context (PostgreSQL lookup)
- SessionStore.list_sessions_for_user with context_id filter
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.sdk.session_handler import SessionHandler
from pilot_space.ai.session.session_manager import (
    AISession,
    SessionManager,
)


class DictBackedRedis:
    """In-memory Redis mock that actually stores and retrieves data."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def set(
        self,
        name: str,
        value: Any,
        ttl: int | None = None,
        **kwargs: Any,
    ) -> bool:
        if isinstance(value, dict):
            self._store[name] = json.dumps(value, default=str)
        else:
            self._store[name] = str(value)
        return True

    async def get(self, name: str) -> str | None:
        raw = self._store.get(name)
        if raw is None:
            return None
        # Try to parse as JSON dict (session data)
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        return raw

    async def delete(self, name: str) -> int:
        if name in self._store:
            del self._store[name]
            return 1
        return 0

    async def expire(self, name: str, time: int) -> bool:
        return name in self._store

    async def scan_keys(self, pattern: str) -> list[str]:
        import fnmatch

        return [k for k in self._store if fnmatch.fnmatch(k, pattern)]

    def clear(self) -> None:
        self._store.clear()


@pytest.fixture
def mock_redis() -> DictBackedRedis:
    """Dict-backed Redis mock for realistic session storage."""
    return DictBackedRedis()


@pytest.fixture
def session_manager(mock_redis: DictBackedRedis) -> SessionManager:
    """SessionManager with dict-backed Redis."""
    return SessionManager(redis=mock_redis)  # type: ignore[arg-type]


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock SQLAlchemy async session."""
    return AsyncMock()


@pytest.fixture
def session_handler(
    session_manager: SessionManager,
    mock_db_session: AsyncMock,
) -> SessionHandler:
    """SessionHandler with dict-backed Redis and mock DB."""
    return SessionHandler(
        session_manager=session_manager,
        db_session=mock_db_session,
    )


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def workspace_id() -> UUID:
    return uuid4()


@pytest.fixture
def note_id() -> UUID:
    return uuid4()


class TestCreateSessionWithContextId:
    """Test that create_session passes context_id to SessionManager."""

    @pytest.mark.asyncio
    async def test_creates_session_with_context_id(
        self,
        session_handler: SessionHandler,
        user_id: UUID,
        workspace_id: UUID,
        note_id: UUID,
    ) -> None:
        """Session created with context_id stores it for later lookup."""
        session = await session_handler.create_session(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="conversation",
            context_id=note_id,
        )

        assert session.session_id is not None
        assert session.workspace_id == workspace_id
        assert session.user_id == user_id
        assert session.context_id == note_id

    @pytest.mark.asyncio
    async def test_creates_session_without_context_id(
        self,
        session_handler: SessionHandler,
        user_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """Session created without context_id has None (backward compat)."""
        session = await session_handler.create_session(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="conversation",
        )

        assert session.context_id is None

    @pytest.mark.asyncio
    async def test_context_id_stored_in_redis_index(
        self,
        session_handler: SessionHandler,
        mock_redis: DictBackedRedis,
        user_id: UUID,
        workspace_id: UUID,
        note_id: UUID,
    ) -> None:
        """Creating session with context_id populates Redis index key."""
        await session_handler.create_session(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="conversation",
            context_id=note_id,
        )

        # Verify index key exists with note_id in key name
        index_keys = [k for k in mock_redis._store if "index" in k]
        assert len(index_keys) >= 1
        # At least one index key should contain the note_id
        note_in_key = any(str(note_id) in k for k in index_keys)
        assert note_in_key, f"No index key contains note_id. Keys: {index_keys}"


class TestGetSessionByContext:
    """Test session lookup by context_id (note_id)."""

    @pytest.mark.asyncio
    async def test_finds_session_in_redis(
        self,
        session_handler: SessionHandler,
        user_id: UUID,
        workspace_id: UUID,
        note_id: UUID,
    ) -> None:
        """When Redis has session indexed by context, return it."""
        created = await session_handler.create_session(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="conversation",
            context_id=note_id,
        )

        found = await session_handler.get_session_by_context(
            user_id=user_id,
            workspace_id=workspace_id,
            agent_name="conversation",
            context_id=note_id,
        )

        assert found is not None
        assert found.session_id == created.session_id
        assert found.context_id == note_id

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_context(
        self,
        session_handler: SessionHandler,
        user_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """When no session exists for context, return None."""
        found = await session_handler.get_session_by_context(
            user_id=user_id,
            workspace_id=workspace_id,
            agent_name="conversation",
            context_id=uuid4(),
        )

        assert found is None

    @pytest.mark.asyncio
    async def test_rejects_workspace_mismatch(
        self,
        session_handler: SessionHandler,
        user_id: UUID,
        workspace_id: UUID,
        note_id: UUID,
    ) -> None:
        """Session belonging to different workspace is rejected."""
        await session_handler.create_session(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="conversation",
            context_id=note_id,
        )

        other_workspace = uuid4()
        found = await session_handler.get_session_by_context(
            user_id=user_id,
            workspace_id=other_workspace,
            agent_name="conversation",
            context_id=note_id,
        )

        assert found is None

    @pytest.mark.asyncio
    async def test_different_notes_get_different_sessions(
        self,
        session_handler: SessionHandler,
        user_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """Each note_id maps to its own session."""
        note_a = uuid4()
        note_b = uuid4()

        session_a = await session_handler.create_session(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="conversation",
            context_id=note_a,
        )

        session_b = await session_handler.create_session(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="conversation",
            context_id=note_b,
        )

        found_a = await session_handler.get_session_by_context(
            user_id=user_id,
            workspace_id=workspace_id,
            agent_name="conversation",
            context_id=note_a,
        )

        found_b = await session_handler.get_session_by_context(
            user_id=user_id,
            workspace_id=workspace_id,
            agent_name="conversation",
            context_id=note_b,
        )

        assert found_a is not None
        assert found_b is not None
        assert found_a.session_id != found_b.session_id
        assert found_a.session_id == session_a.session_id
        assert found_b.session_id == session_b.session_id


class TestExplicitSessionIdPriority:
    """Test that explicit session_id takes priority over context lookup."""

    @pytest.mark.asyncio
    async def test_explicit_session_id_used_over_context(
        self,
        session_handler: SessionHandler,
        user_id: UUID,
        workspace_id: UUID,
        note_id: UUID,
    ) -> None:
        """When both session_id and note_id exist, session_id wins."""
        first = await session_handler.create_session(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="conversation",
            context_id=note_id,
        )

        second = await session_handler.create_session(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="conversation",
            context_id=note_id,
        )

        # Explicit get_session returns the exact session requested
        explicit = await session_handler.get_session(
            first.session_id,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        assert explicit is not None
        assert explicit.session_id == first.session_id

        # Context lookup returns the latest (index overwritten)
        by_context = await session_handler.get_session_by_context(
            user_id=user_id,
            workspace_id=workspace_id,
            agent_name="conversation",
            context_id=note_id,
        )
        assert by_context is not None
        assert by_context.session_id == second.session_id


class TestPostgreSQLFallback:
    """Test database fallback when Redis session expires."""

    @pytest.mark.asyncio
    async def test_falls_back_to_db_when_redis_empty(
        self,
        session_manager: SessionManager,
        mock_db_session: AsyncMock,
        user_id: UUID,
        workspace_id: UUID,
        note_id: UUID,
    ) -> None:
        """When Redis has no session, try PostgreSQL via SessionStore."""
        # Use a fresh handler with empty Redis (no sessions created)
        handler = SessionHandler(
            session_manager=session_manager,
            db_session=mock_db_session,
        )

        mock_restored_session = AISession(
            user_id=user_id,
            workspace_id=workspace_id,
            agent_name="conversation",
            context_id=note_id,
        )

        with patch(
            "pilot_space.ai.sdk.session_store.SessionStore.load_by_context",
            new_callable=AsyncMock,
            return_value=mock_restored_session,
        ) as mock_load:
            found = await handler.get_session_by_context(
                user_id=user_id,
                workspace_id=workspace_id,
                agent_name="conversation",
                context_id=note_id,
            )

        assert found is not None
        assert found.context_id == note_id
        mock_load.assert_called_once_with(
            user_id=user_id,
            agent_name="conversation",
            context_id=note_id,
        )

    @pytest.mark.asyncio
    async def test_returns_none_when_both_redis_and_db_empty(
        self,
        session_manager: SessionManager,
        mock_db_session: AsyncMock,
        user_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """When neither Redis nor PostgreSQL has session, return None."""
        handler = SessionHandler(
            session_manager=session_manager,
            db_session=mock_db_session,
        )

        with patch(
            "pilot_space.ai.sdk.session_store.SessionStore.load_by_context",
            new_callable=AsyncMock,
            return_value=None,
        ):
            found = await handler.get_session_by_context(
                user_id=user_id,
                workspace_id=workspace_id,
                agent_name="conversation",
                context_id=uuid4(),
            )

        assert found is None

    @pytest.mark.asyncio
    async def test_no_db_fallback_without_db_session(
        self,
        session_manager: SessionManager,
        user_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """When db_session is None, skip PostgreSQL fallback gracefully."""
        handler = SessionHandler(
            session_manager=session_manager,
            db_session=None,
        )

        found = await handler.get_session_by_context(
            user_id=user_id,
            workspace_id=workspace_id,
            agent_name="conversation",
            context_id=uuid4(),
        )

        assert found is None


class TestPersistSession:
    """Test SessionHandler.persist_session saves Redis session to PostgreSQL."""

    @pytest.mark.asyncio
    async def test_persist_session_calls_save_to_db(
        self,
        session_handler: SessionHandler,
        user_id: UUID,
        workspace_id: UUID,
        note_id: UUID,
    ) -> None:
        """persist_session delegates to SessionStore.save_to_db."""
        session = await session_handler.create_session(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="conversation",
            context_id=note_id,
        )

        with patch(
            "pilot_space.ai.sdk.session_store.SessionStore.save_to_db",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_save:
            result = await session_handler.persist_session(session.session_id)

        assert result is True
        mock_save.assert_called_once_with(session.session_id)

    @pytest.mark.asyncio
    async def test_persist_session_skips_without_db(
        self,
        session_manager: SessionManager,
    ) -> None:
        """persist_session returns False when no db_session is available."""
        handler = SessionHandler(
            session_manager=session_manager,
            db_session=None,
        )

        result = await handler.persist_session(uuid4())
        assert result is False


class TestListSessionsContextIdFilter:
    """Test SessionStore.list_sessions_for_user with context_id filter."""

    @pytest.mark.asyncio
    async def test_list_sessions_passes_context_id_filter(
        self,
        user_id: UUID,
        workspace_id: UUID,
        note_id: UUID,
    ) -> None:
        """list_sessions_for_user passes context_id to SQL query."""
        from unittest.mock import MagicMock

        mock_db = AsyncMock()
        # scalars() is sync, .all() is sync — only execute() is async
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        mock_session_manager = AsyncMock()

        from pilot_space.ai.sdk.session_store import SessionStore

        store = SessionStore(mock_session_manager, mock_db)

        result = await store.list_sessions_for_user(
            user_id=user_id,
            context_id=note_id,
        )

        assert result == []
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_sessions_without_context_id(
        self,
        user_id: UUID,
    ) -> None:
        """list_sessions_for_user works without context_id (backward compat)."""
        from unittest.mock import MagicMock

        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        mock_session_manager = AsyncMock()

        from pilot_space.ai.sdk.session_store import SessionStore

        store = SessionStore(mock_session_manager, mock_db)

        result = await store.list_sessions_for_user(
            user_id=user_id,
        )

        assert result == []
        mock_db.execute.assert_called_once()
