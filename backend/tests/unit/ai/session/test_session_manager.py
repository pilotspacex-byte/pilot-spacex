"""Unit tests for AI SessionManager.

Tests session lifecycle, message management, cost tracking,
and Redis storage operations.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.exceptions import AIError
from pilot_space.ai.session.session_manager import (
    SESSION_TTL_SECONDS,
    AIMessage,
    AISession,
    SessionExpiredError,
    SessionManager,
    SessionNotFoundError,
)


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Mock Redis client."""
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.scan_keys = AsyncMock(return_value=[])
    return redis


@pytest.fixture
def session_manager(mock_redis: AsyncMock) -> SessionManager:
    """SessionManager with mocked Redis."""
    return SessionManager(redis=mock_redis)


@pytest.fixture
def sample_user_id() -> UUID:
    """Sample user UUID."""
    return uuid4()


@pytest.fixture
def sample_workspace_id() -> UUID:
    """Sample workspace UUID."""
    return uuid4()


@pytest.fixture
def sample_context_id() -> UUID:
    """Sample context UUID."""
    return uuid4()


class TestAIMessage:
    """Test AIMessage dataclass."""

    def test_message_creation(self) -> None:
        """Verify message creation with defaults."""
        msg = AIMessage(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None
        assert msg.tokens is None
        assert msg.cost_usd is None

    def test_message_with_metadata(self) -> None:
        """Verify message with tokens and cost."""
        msg = AIMessage(
            role="assistant",
            content="Response",
            tokens=100,
            cost_usd=0.002,
        )

        assert msg.tokens == 100
        assert msg.cost_usd == 0.002

    def test_message_to_dict(self) -> None:
        """Verify serialization to dict."""
        now = datetime.now(UTC)
        msg = AIMessage(
            role="user",
            content="Test",
            timestamp=now,
            tokens=50,
            cost_usd=0.001,
        )

        result = msg.to_dict()

        assert result["role"] == "user"
        assert result["content"] == "Test"
        assert result["timestamp"] == now.isoformat()
        assert result["tokens"] == 50
        assert result["cost_usd"] == 0.001

    def test_message_from_dict(self) -> None:
        """Verify deserialization from dict."""
        data = {
            "role": "assistant",
            "content": "Response",
            "timestamp": "2025-01-26T10:00:00+00:00",
            "tokens": 100,
            "cost_usd": 0.002,
        }

        msg = AIMessage.from_dict(data)

        assert msg.role == "assistant"
        assert msg.content == "Response"
        assert msg.tokens == 100
        assert msg.cost_usd == 0.002

    def test_message_from_dict_minimal(self) -> None:
        """Verify deserialization with minimal fields."""
        data = {
            "role": "user",
            "content": "Test",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        msg = AIMessage.from_dict(data)

        assert msg.role == "user"
        assert msg.content == "Test"
        assert msg.tokens is None
        assert msg.cost_usd is None


class TestAISession:
    """Test AISession dataclass."""

    def test_session_creation(self, sample_user_id: UUID, sample_workspace_id: UUID) -> None:
        """Verify session creation with defaults."""
        session = AISession(
            user_id=sample_user_id,
            workspace_id=sample_workspace_id,
            agent_name="TestAgent",
        )

        assert session.id is not None
        assert session.user_id == sample_user_id
        assert session.workspace_id == sample_workspace_id
        assert session.agent_name == "TestAgent"
        assert session.context_id is None
        assert session.context == {}
        assert session.messages == []
        assert session.total_cost_usd == 0.0
        assert session.turn_count == 0
        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.expires_at is not None

    def test_session_with_context(
        self,
        sample_user_id: UUID,
        sample_workspace_id: UUID,
        sample_context_id: UUID,
    ) -> None:
        """Verify session creation with context."""
        initial_context = {"issue_id": str(sample_context_id), "priority": "high"}
        session = AISession(
            user_id=sample_user_id,
            workspace_id=sample_workspace_id,
            agent_name="AIContextAgent",
            context_id=sample_context_id,
            context=initial_context,
        )

        assert session.context_id == sample_context_id
        assert session.context["priority"] == "high"

    def test_session_to_dict(self, sample_user_id: UUID, sample_workspace_id: UUID) -> None:
        """Verify session serialization."""
        session = AISession(
            user_id=sample_user_id,
            workspace_id=sample_workspace_id,
            agent_name="TestAgent",
        )

        result = session.to_dict()

        assert result["user_id"] == str(sample_user_id)
        assert result["workspace_id"] == str(sample_workspace_id)
        assert result["agent_name"] == "TestAgent"
        assert result["context_id"] is None
        assert result["messages"] == []
        assert result["total_cost_usd"] == 0.0
        assert result["turn_count"] == 0

    def test_session_to_dict_with_messages(
        self,
        sample_user_id: UUID,
        sample_workspace_id: UUID,
    ) -> None:
        """Verify session serialization with messages."""
        session = AISession(
            user_id=sample_user_id,
            workspace_id=sample_workspace_id,
            agent_name="TestAgent",
            messages=[
                AIMessage(role="user", content="Hello"),
                AIMessage(role="assistant", content="Hi there"),
            ],
        )

        result = session.to_dict()

        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][1]["role"] == "assistant"

    def test_session_from_dict(self) -> None:
        """Verify session deserialization."""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "agent_name": "TestAgent",
            "context_id": None,
            "context": {},
            "messages": [],
            "total_cost_usd": 0.0,
            "turn_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=1800)).isoformat(),
        }

        session = AISession.from_dict(data)

        assert str(session.id) == data["id"]
        assert str(session.user_id) == data["user_id"]
        assert str(session.workspace_id) == data["workspace_id"]

    def test_session_from_dict_with_messages(self) -> None:
        """Verify session deserialization with messages."""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "agent_name": "TestAgent",
            "context_id": None,
            "context": {},
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "tokens": None,
                    "cost_usd": None,
                },
            ],
            "total_cost_usd": 0.0,
            "turn_count": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=1800)).isoformat(),
        }

        session = AISession.from_dict(data)

        assert len(session.messages) == 1
        assert session.messages[0].role == "user"

    def test_is_expired_false(self, sample_user_id: UUID, sample_workspace_id: UUID) -> None:
        """Verify session is not expired."""
        session = AISession(
            user_id=sample_user_id,
            workspace_id=sample_workspace_id,
            agent_name="TestAgent",
        )

        assert not session.is_expired()

    def test_is_expired_true(self, sample_user_id: UUID, sample_workspace_id: UUID) -> None:
        """Verify expired session detection."""
        session = AISession(
            user_id=sample_user_id,
            workspace_id=sample_workspace_id,
            agent_name="TestAgent",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )

        assert session.is_expired()


class TestSessionManager:
    """Test SessionManager operations."""

    @pytest.mark.asyncio
    async def test_create_session(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
        sample_user_id: UUID,
        sample_workspace_id: UUID,
    ) -> None:
        """Verify session creation."""
        session = await session_manager.create_session(
            user_id=sample_user_id,
            workspace_id=sample_workspace_id,
            agent_name="TestAgent",
        )

        assert session.user_id == sample_user_id
        assert session.workspace_id == sample_workspace_id
        assert session.agent_name == "TestAgent"

        # Verify Redis calls
        assert mock_redis.set.call_count == 2  # Session + index

    @pytest.mark.asyncio
    async def test_create_session_with_context(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
        sample_user_id: UUID,
        sample_workspace_id: UUID,
        sample_context_id: UUID,
    ) -> None:
        """Verify session creation with context."""
        initial_context = {"key": "value"}

        session = await session_manager.create_session(
            user_id=sample_user_id,
            workspace_id=sample_workspace_id,
            agent_name="AIContextAgent",
            context_id=sample_context_id,
            initial_context=initial_context,
        )

        assert session.context_id == sample_context_id
        assert session.context == initial_context

    @pytest.mark.asyncio
    async def test_create_session_redis_failure(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
        sample_user_id: UUID,
        sample_workspace_id: UUID,
    ) -> None:
        """Verify error handling when Redis fails."""
        mock_redis.set.return_value = False

        with pytest.raises(AIError, match="Failed to create session"):
            await session_manager.create_session(
                user_id=sample_user_id,
                workspace_id=sample_workspace_id,
                agent_name="TestAgent",
            )

    @pytest.mark.asyncio
    async def test_get_session(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
        sample_user_id: UUID,
        sample_workspace_id: UUID,
    ) -> None:
        """Verify session retrieval."""
        session_id = uuid4()
        session_data = {
            "id": str(session_id),
            "user_id": str(sample_user_id),
            "workspace_id": str(sample_workspace_id),
            "agent_name": "TestAgent",
            "context_id": None,
            "context": {},
            "messages": [],
            "total_cost_usd": 0.0,
            "turn_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=1800)).isoformat(),
        }
        mock_redis.get.return_value = session_data

        session = await session_manager.get_session(session_id)

        assert session.id == session_id
        assert session.user_id == sample_user_id
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_not_found(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify error when session not found."""
        mock_redis.get.return_value = None
        session_id = uuid4()

        with pytest.raises(SessionNotFoundError):
            await session_manager.get_session(session_id)

    @pytest.mark.asyncio
    async def test_get_session_expired(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
        sample_user_id: UUID,
        sample_workspace_id: UUID,
    ) -> None:
        """Verify error when session has expired."""
        session_id = uuid4()
        session_data = {
            "id": str(session_id),
            "user_id": str(sample_user_id),
            "workspace_id": str(sample_workspace_id),
            "agent_name": "TestAgent",
            "context_id": None,
            "context": {},
            "messages": [],
            "total_cost_usd": 0.0,
            "turn_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        }
        mock_redis.get.return_value = session_data

        with pytest.raises(SessionExpiredError):
            await session_manager.get_session(session_id)

    @pytest.mark.asyncio
    async def test_update_session(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
        sample_user_id: UUID,
        sample_workspace_id: UUID,
    ) -> None:
        """Verify session update."""
        session_id = uuid4()
        session_data: dict[str, Any] = {
            "id": str(session_id),
            "user_id": str(sample_user_id),
            "workspace_id": str(sample_workspace_id),
            "agent_name": "TestAgent",
            "context_id": None,
            "context": {},
            "messages": [],
            "total_cost_usd": 0.0,
            "turn_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=1800)).isoformat(),
        }
        mock_redis.get.return_value = session_data

        message = AIMessage(role="user", content="Hello")

        updated = await session_manager.update_session(
            session_id=session_id,
            message=message,
            cost_delta=0.005,
        )

        assert updated.turn_count == 1
        assert len(updated.messages) == 1
        assert updated.total_cost_usd == 0.005

    @pytest.mark.asyncio
    async def test_update_session_with_context(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
        sample_user_id: UUID,
        sample_workspace_id: UUID,
    ) -> None:
        """Verify session update with context merge."""
        session_id = uuid4()
        session_data: dict[str, Any] = {
            "id": str(session_id),
            "user_id": str(sample_user_id),
            "workspace_id": str(sample_workspace_id),
            "agent_name": "TestAgent",
            "context_id": None,
            "context": {"key1": "value1"},
            "messages": [],
            "total_cost_usd": 0.0,
            "turn_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=1800)).isoformat(),
        }
        mock_redis.get.return_value = session_data

        updated = await session_manager.update_session(
            session_id=session_id,
            context_update={"key2": "value2"},
        )

        assert updated.context["key1"] == "value1"
        assert updated.context["key2"] == "value2"

    @pytest.mark.asyncio
    async def test_end_session(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
        sample_user_id: UUID,
        sample_workspace_id: UUID,
    ) -> None:
        """Verify session cleanup."""
        session_id = uuid4()
        session_data = {
            "id": str(session_id),
            "user_id": str(sample_user_id),
            "workspace_id": str(sample_workspace_id),
            "agent_name": "TestAgent",
            "context_id": None,
            "context": {},
            "messages": [],
            "total_cost_usd": 0.0,
            "turn_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=1800)).isoformat(),
        }
        mock_redis.get.return_value = session_data

        result = await session_manager.end_session(session_id)

        assert result is True
        assert mock_redis.delete.call_count == 2  # Session + index

    @pytest.mark.asyncio
    async def test_end_session_not_found(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify cleanup when session doesn't exist."""
        mock_redis.get.return_value = None
        session_id = uuid4()

        result = await session_manager.end_session(session_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_active_session(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
        sample_user_id: UUID,
        sample_workspace_id: UUID,
        sample_context_id: UUID,
    ) -> None:
        """Verify active session lookup."""
        session_id = uuid4()
        session_data = {
            "id": str(session_id),
            "user_id": str(sample_user_id),
            "workspace_id": str(sample_workspace_id),
            "agent_name": "TestAgent",
            "context_id": str(sample_context_id),
            "context": {},
            "messages": [],
            "total_cost_usd": 0.0,
            "turn_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=1800)).isoformat(),
        }

        # Mock Redis to return index then session
        def get_side_effect(key: str) -> str | dict[str, Any] | None:
            if ":index:" in key:
                return str(session_id)
            return session_data

        mock_redis.get.side_effect = get_side_effect

        session = await session_manager.get_active_session(
            user_id=sample_user_id,
            agent_name="TestAgent",
            context_id=sample_context_id,
        )

        assert session is not None
        assert session.id == session_id

    @pytest.mark.asyncio
    async def test_get_active_session_not_found(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
        sample_user_id: UUID,
    ) -> None:
        """Verify None when no active session."""
        mock_redis.get.return_value = None

        session = await session_manager.get_active_session(
            user_id=sample_user_id,
            agent_name="TestAgent",
        )

        assert session is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(
        self,
        session_manager: SessionManager,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify cleanup of expired sessions."""
        expired_session = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "agent_name": "TestAgent",
            "context_id": None,
            "context": {},
            "messages": [],
            "total_cost_usd": 0.0,
            "turn_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        }

        mock_redis.scan_keys.return_value = ["ai_session:abc123"]
        mock_redis.get.return_value = expired_session

        cleaned = await session_manager.cleanup_expired_sessions()

        assert cleaned == 1
        mock_redis.delete.assert_called_once()


class TestSessionConstants:
    """Test module constants."""

    def test_session_ttl_seconds(self) -> None:
        """Verify TTL constant."""
        assert SESSION_TTL_SECONDS == 1800  # 30 minutes
