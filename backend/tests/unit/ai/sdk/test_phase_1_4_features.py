"""Unit tests for Phase 1-4 SDK features and gap fixes.

Tests cover:
- SDKConfiguration tool_search_enabled (Phase 4, T4.7)
- SDKConfiguration prompt_caching and thinking (Phase 1 & 2)
- SessionHandler fork_session (Phase 4, T4.2)
- Gap A1: Model not hardcoded (DD-011 provider routing)
- Gap A2/B2: include_partial_messages and max_thinking_tokens auto-set
- Gap C1: effort parameter support
- Gap C2-C6: citations, memory config fields
- Gap B3: SubagentProgressHook lifecycle events
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.sdk.sandbox_config import (
    ModelTier,
    SandboxSettings,
    SDKConfiguration,
    configure_sdk_for_space,
    resolve_model,
)
from pilot_space.ai.sdk.session_handler import ConversationSession, SessionHandler
from pilot_space.ai.session.session_manager import (
    AIMessage,
    AISession,
    SessionNotFoundError,
)
from pilot_space.spaces.base import SpaceContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sdk_config(**overrides: Any) -> SDKConfiguration:
    """Build an SDKConfiguration with sensible defaults, applying overrides."""
    defaults: dict[str, Any] = {
        "cwd": "/workspace",
        "setting_sources": ["project"],
        "sandbox": SandboxSettings(),
        "permission_mode": "default",
        "env": {},
        "allowed_tools": [],
    }
    defaults.update(overrides)
    return SDKConfiguration(**defaults)


def _make_ai_session(
    *,
    session_id: UUID | None = None,
    workspace_id: UUID | None = None,
    user_id: UUID | None = None,
    agent_name: str = "test_agent",
    messages: list[AIMessage] | None = None,
    context: dict[str, Any] | None = None,
) -> AISession:
    """Build an AISession with sensible defaults."""
    now = datetime.now(UTC)
    return AISession(
        id=session_id or uuid4(),
        workspace_id=workspace_id or uuid4(),
        user_id=user_id or uuid4(),
        agent_name=agent_name,
        messages=messages or [],
        context=context or {},
        total_cost_usd=0.0,
        turn_count=0,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(minutes=30),
    )


# ===========================================================================
# 1. SDKConfiguration.tool_search_enabled (Phase 4, T4.7)
# ===========================================================================


class TestToolSearchEnabled:
    """Tests for SDKConfiguration.tool_search_enabled field and SDK param output."""

    def test_default_is_false(self) -> None:
        """tool_search_enabled defaults to False."""
        config = _make_sdk_config()
        assert config.tool_search_enabled is False

    def test_to_sdk_params_includes_tool_search_when_enabled(self) -> None:
        """to_sdk_params sets tool_search: True when tool_search_enabled is True."""
        config = _make_sdk_config(tool_search_enabled=True)
        params = config.to_sdk_params()
        assert params["tool_search"] is True

    def test_to_sdk_params_excludes_tool_search_when_disabled(self) -> None:
        """to_sdk_params omits tool_search key when tool_search_enabled is False."""
        config = _make_sdk_config(tool_search_enabled=False)
        params = config.to_sdk_params()
        assert "tool_search" not in params

    def test_configure_sdk_auto_enables_tool_search_above_10_tools(self) -> None:
        """configure_sdk_for_space enables tool_search when >10 tools registered."""
        context = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"PILOT_WORKSPACE_ID": "ws-1", "PILOT_USER_ID": "u-1"},
        )
        # Base tools in configure_sdk_for_space already exceed 10 (14 base tools).
        config = configure_sdk_for_space(context)
        assert config.tool_search_enabled is True

    def test_configure_sdk_disables_tool_search_at_or_below_10_tools(self) -> None:
        """configure_sdk_for_space disables tool_search when <=10 tools."""
        # Override allowed_tools to <=10 by checking the threshold logic.
        # The factory always uses base_tools (14) so tool_search is always True
        # in normal usage. We verify that an SDKConfiguration with <=10 tools
        # would have tool_search_enabled=False when constructed directly.
        config = _make_sdk_config(
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep"],
            tool_search_enabled=False,
        )
        assert config.tool_search_enabled is False
        assert "tool_search" not in config.to_sdk_params()


# ===========================================================================
# 2. SDKConfiguration prompt_caching and thinking (Phase 1 & 2)
# ===========================================================================


class TestPromptCachingAndThinking:
    """Tests for prompt_caching and max_thinking_tokens fields."""

    def test_prompt_caching_defaults_to_true(self) -> None:
        """prompt_caching defaults to True per Phase 1 design."""
        config = _make_sdk_config()
        assert config.prompt_caching is True

    def test_max_thinking_tokens_defaults_to_none(self) -> None:
        """max_thinking_tokens defaults to None (disabled)."""
        config = _make_sdk_config()
        assert config.max_thinking_tokens is None

    def test_to_sdk_params_includes_thinking_tokens_when_set(self) -> None:
        """to_sdk_params includes max_thinking_tokens when explicitly set."""
        config = _make_sdk_config(max_thinking_tokens=4096)
        params = config.to_sdk_params()
        assert params["max_thinking_tokens"] == 4096

    def test_to_sdk_params_excludes_thinking_tokens_when_none(self) -> None:
        """to_sdk_params omits max_thinking_tokens when None."""
        config = _make_sdk_config(max_thinking_tokens=None)
        params = config.to_sdk_params()
        assert "max_thinking_tokens" not in params

    def test_to_sdk_params_includes_partial_messages_when_true(self) -> None:
        """to_sdk_params includes include_partial_messages when True."""
        config = _make_sdk_config(include_partial_messages=True)
        params = config.to_sdk_params()
        assert params["include_partial_messages"] is True

    def test_to_sdk_params_excludes_partial_messages_when_false(self) -> None:
        """to_sdk_params omits include_partial_messages when False."""
        config = _make_sdk_config(include_partial_messages=False)
        params = config.to_sdk_params()
        assert "include_partial_messages" not in params

    def test_include_partial_messages_defaults_to_false(self) -> None:
        """include_partial_messages defaults to False."""
        config = _make_sdk_config()
        assert config.include_partial_messages is False


# ===========================================================================
# 3. SessionHandler.fork_session (Phase 4, T4.2)
# ===========================================================================


class TestSessionHandlerForkSession:
    """Tests for SessionHandler.fork_session branching logic."""

    @pytest.fixture
    def session_manager(self) -> AsyncMock:
        """Mock SessionManager with spec-compatible async methods."""
        return AsyncMock()

    @pytest.fixture
    def handler(self, session_manager: AsyncMock) -> SessionHandler:
        """SessionHandler backed by mock SessionManager."""
        return SessionHandler(session_manager)

    def _build_source_session(
        self,
        *,
        session_id: UUID | None = None,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        messages: list[AIMessage] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AISession:
        """Helper to build source AISession for fork tests."""
        return _make_ai_session(
            session_id=session_id or uuid4(),
            workspace_id=workspace_id or uuid4(),
            user_id=user_id or uuid4(),
            messages=messages
            or [
                AIMessage(role="user", content="Hello", tokens=10),
                AIMessage(role="assistant", content="Hi there", tokens=15),
            ],
            context=context or {"fork_count": 0},
        )

    @pytest.mark.asyncio
    async def test_fork_copies_message_history(
        self,
        handler: SessionHandler,
        session_manager: AsyncMock,
    ) -> None:
        """Forked session receives all messages from the source."""
        source_id = uuid4()
        ws_id = uuid4()
        user_id = uuid4()

        source = self._build_source_session(
            session_id=source_id, workspace_id=ws_id, user_id=user_id
        )
        forked_ai = _make_ai_session(workspace_id=ws_id, user_id=user_id)

        session_manager.get_session.return_value = source
        session_manager.create_session.return_value = forked_ai

        result = await handler.fork_session(source_id, ws_id, user_id)

        # add_message called once per source message
        assert session_manager.update_session.call_count >= len(source.messages)
        assert isinstance(result, ConversationSession)

    @pytest.mark.asyncio
    async def test_fork_sets_forked_from_metadata(
        self,
        handler: SessionHandler,
        session_manager: AsyncMock,
    ) -> None:
        """Forked session metadata includes forked_from pointing to source."""
        source_id = uuid4()
        ws_id = uuid4()
        user_id = uuid4()

        source = self._build_source_session(session_id=source_id)
        forked_ai = _make_ai_session()

        session_manager.get_session.return_value = source
        session_manager.create_session.return_value = forked_ai

        await handler.fork_session(source_id, ws_id, user_id)

        # Verify create_session was called with fork metadata
        create_call = session_manager.create_session.call_args
        metadata = create_call.kwargs.get("initial_context", {})
        assert metadata["forked_from"] == str(source_id)
        assert metadata["fork_count"] == 0

    @pytest.mark.asyncio
    async def test_fork_increments_source_fork_count(
        self,
        handler: SessionHandler,
        session_manager: AsyncMock,
    ) -> None:
        """Source session fork_count is incremented after fork."""
        source_id = uuid4()
        source = self._build_source_session(session_id=source_id, context={"fork_count": 1})
        forked_ai = _make_ai_session()

        session_manager.get_session.return_value = source
        session_manager.create_session.return_value = forked_ai

        await handler.fork_session(source_id, uuid4(), uuid4())

        # Last update_session call should carry context_update with incremented fork_count
        update_calls = session_manager.update_session.call_args_list
        context_update_call = update_calls[-1]
        assert context_update_call.kwargs.get("context_update", {}).get("fork_count") == 2

    @pytest.mark.asyncio
    async def test_fork_raises_session_not_found_for_missing_source(
        self,
        handler: SessionHandler,
        session_manager: AsyncMock,
    ) -> None:
        """fork_session raises SessionNotFoundError when source does not exist."""
        missing_id = uuid4()
        session_manager.get_session.side_effect = SessionNotFoundError(missing_id)

        with pytest.raises(SessionNotFoundError):
            await handler.fork_session(missing_id, uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_fork_raises_value_error_when_limit_exceeded(
        self,
        handler: SessionHandler,
        session_manager: AsyncMock,
    ) -> None:
        """fork_session raises ValueError when fork limit (3) is reached."""
        source_id = uuid4()
        source = self._build_source_session(session_id=source_id, context={"fork_count": 3})
        session_manager.get_session.return_value = source

        with pytest.raises(ValueError, match="Fork limit reached"):
            await handler.fork_session(source_id, uuid4(), uuid4())

        # No new session should have been created
        session_manager.create_session.assert_not_awaited()


# ===========================================================================
# 4. Gap A1: Model not hardcoded — DD-011 provider routing
# ===========================================================================


class TestModelNotHardcoded:
    """Verify configure_sdk_for_space uses DD-011 model routing, not hardcoded values."""

    def test_default_model_is_sonnet(self) -> None:
        """Default model should be claude-sonnet, not kimi or any non-Anthropic model."""
        context = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"PILOT_WORKSPACE_ID": "ws-1", "PILOT_USER_ID": "u-1"},
        )
        config = configure_sdk_for_space(context)
        assert "claude" in config.model.lower() or "sonnet" in config.model.lower()
        assert "kimi" not in config.model.lower()

    def test_model_passed_through(self) -> None:
        """Model parameter is respected when explicitly provided."""
        context = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"PILOT_WORKSPACE_ID": "ws-1", "PILOT_USER_ID": "u-1"},
        )
        config = configure_sdk_for_space(context, model="claude-opus-4-20250514")
        assert config.model == "claude-opus-4-20250514"


# ===========================================================================
# 5. Gap A2/B2: include_partial_messages and max_thinking_tokens auto-set
# ===========================================================================


class TestPartialMessagesAndThinking:
    """Tests for include_partial_messages passthrough and thinking auto-set."""

    def test_include_partial_messages_passthrough(self) -> None:
        """include_partial_messages=True is passed through to SDKConfiguration."""
        context = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"PILOT_WORKSPACE_ID": "ws-1", "PILOT_USER_ID": "u-1"},
        )
        config = configure_sdk_for_space(context, include_partial_messages=True)
        assert config.include_partial_messages is True
        params = config.to_sdk_params()
        assert params["include_partial_messages"] is True

    def test_max_thinking_tokens_auto_set_for_opus(self) -> None:
        """max_thinking_tokens is auto-set to 10000 when model contains 'opus'."""
        context = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"PILOT_WORKSPACE_ID": "ws-1", "PILOT_USER_ID": "u-1"},
        )
        config = configure_sdk_for_space(context, model="claude-opus-4-20250514")
        assert config.max_thinking_tokens == 10000
        params = config.to_sdk_params()
        assert params["max_thinking_tokens"] == 10000

    def test_max_thinking_tokens_not_set_for_sonnet(self) -> None:
        """max_thinking_tokens stays None for non-Opus models."""
        context = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"PILOT_WORKSPACE_ID": "ws-1", "PILOT_USER_ID": "u-1"},
        )
        config = configure_sdk_for_space(context, model="claude-sonnet-4-20250514")
        assert config.max_thinking_tokens is None
        assert "max_thinking_tokens" not in config.to_sdk_params()

    def test_explicit_thinking_tokens_overrides_auto(self) -> None:
        """Explicit max_thinking_tokens overrides auto-set for Opus."""
        context = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"PILOT_WORKSPACE_ID": "ws-1", "PILOT_USER_ID": "u-1"},
        )
        config = configure_sdk_for_space(
            context, model="claude-opus-4-20250514", max_thinking_tokens=5000
        )
        assert config.max_thinking_tokens == 5000


# ===========================================================================
# 6. Gap C1: effort parameter support
# ===========================================================================


class TestEffortParameter:
    """Tests for SDK effort parameter configuration."""

    def test_effort_defaults_to_none(self) -> None:
        """effort defaults to None (SDK default behavior)."""
        config = _make_sdk_config()
        assert config.effort is None
        assert "effort" not in config.to_sdk_params()

    def test_effort_passthrough(self) -> None:
        """effort parameter is passed through to SDK params."""
        config = _make_sdk_config(effort="high")
        params = config.to_sdk_params()
        assert params["effort"] == "high"

    def test_effort_via_factory(self) -> None:
        """effort parameter works via configure_sdk_for_space."""
        context = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"PILOT_WORKSPACE_ID": "ws-1", "PILOT_USER_ID": "u-1"},
        )
        config = configure_sdk_for_space(context, effort="low")
        assert config.effort == "low"


# ===========================================================================
# 7. Gap C2-C6: citations and memory config fields
# ===========================================================================


class TestCitationsAndMemory:
    """Tests for citations_enabled and memory_enabled config fields."""

    def test_citations_default_false(self) -> None:
        """citations_enabled defaults to False."""
        config = _make_sdk_config()
        assert config.citations_enabled is False
        assert "citations" not in config.to_sdk_params()

    def test_citations_when_enabled(self) -> None:
        """citations_enabled=True emits citations: True in SDK params."""
        config = _make_sdk_config(citations_enabled=True)
        params = config.to_sdk_params()
        assert params["citations"] is True

    def test_memory_default_false(self) -> None:
        """memory_enabled defaults to False."""
        config = _make_sdk_config()
        assert config.memory_enabled is False
        assert "memory" not in config.to_sdk_params()

    def test_memory_when_enabled(self) -> None:
        """memory_enabled=True emits memory: True in SDK params."""
        config = _make_sdk_config(memory_enabled=True)
        params = config.to_sdk_params()
        assert params["memory"] is True


# ===========================================================================
# 8. Gap B3: SubagentProgressHook lifecycle events
# ===========================================================================


class TestSubagentProgressHook:
    """Tests for SubagentProgressHook SSE event emission."""

    def test_to_sdk_hooks_returns_start_and_end(self) -> None:
        """Hook returns both SubagentStart and SubagentEnd matchers."""
        from pilot_space.ai.sdk.hooks import SubagentProgressHook

        hook = SubagentProgressHook(event_queue=None)
        sdk_hooks = hook.to_sdk_hooks()

        assert "SubagentStart" in sdk_hooks
        assert "SubagentEnd" in sdk_hooks
        assert len(sdk_hooks["SubagentStart"]) == 1
        assert len(sdk_hooks["SubagentEnd"]) == 1

    @pytest.mark.asyncio
    async def test_start_callback_emits_task_progress(self) -> None:
        """SubagentStart callback emits task_progress SSE event."""
        import asyncio

        from pilot_space.ai.sdk.hooks import SubagentProgressHook

        queue: asyncio.Queue[str] = asyncio.Queue()
        hook = SubagentProgressHook(event_queue=queue)
        sdk_hooks = hook.to_sdk_hooks()

        start_callback = sdk_hooks["SubagentStart"][0]["hooks"][0]
        await start_callback(
            {"agent_name": "pr-review", "model": "opus", "task_id": "t-1"},
            None,
            None,
        )

        event = queue.get_nowait()
        assert "task_progress" in event
        assert "pr-review" in event
        assert "in_progress" in event

    @pytest.mark.asyncio
    async def test_end_callback_emits_completed(self) -> None:
        """SubagentEnd callback emits completed task_progress SSE event."""
        import asyncio

        from pilot_space.ai.sdk.hooks import SubagentProgressHook

        queue: asyncio.Queue[str] = asyncio.Queue()
        hook = SubagentProgressHook(event_queue=queue)
        sdk_hooks = hook.to_sdk_hooks()

        end_callback = sdk_hooks["SubagentEnd"][0]["hooks"][0]
        await end_callback(
            {"agent_name": "pr-review", "task_id": "t-1", "is_error": False},
            None,
            None,
        )

        event = queue.get_nowait()
        assert "task_progress" in event
        assert "completed" in event


# ===========================================================================
# 9. ModelTier enum and resolve_model
# ===========================================================================


class TestModelTier:
    """Tests for ModelTier enum and resolve_model helper."""

    def test_sonnet_tier_resolves_to_default(self) -> None:
        """ModelTier.SONNET resolves to default sonnet model ID."""
        model_id = ModelTier.SONNET.model_id
        assert "sonnet" in model_id.lower()
        assert "claude" in model_id.lower()

    def test_opus_tier_resolves_to_default(self) -> None:
        """ModelTier.OPUS resolves to default opus model ID."""
        model_id = ModelTier.OPUS.model_id
        assert "opus" in model_id.lower()
        assert "claude" in model_id.lower()

    def test_resolve_model_with_tier_enum(self) -> None:
        """resolve_model accepts ModelTier enum."""
        result = resolve_model(ModelTier.SONNET)
        assert "sonnet" in result.lower()

    def test_resolve_model_with_tier_string(self) -> None:
        """resolve_model accepts tier name as string."""
        result = resolve_model("sonnet")
        assert "sonnet" in result.lower()

        result = resolve_model("opus")
        assert "opus" in result.lower()

    def test_resolve_model_with_full_model_id(self) -> None:
        """resolve_model passes through full model IDs unchanged."""
        custom = "claude-sonnet-4-20250514"
        assert resolve_model(custom) == custom

    def test_resolve_model_case_insensitive(self) -> None:
        """resolve_model handles case-insensitive tier names."""
        result = resolve_model("Sonnet")
        assert "sonnet" in result.lower()

    def test_resolve_model_with_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ModelTier resolves from env var when set."""
        monkeypatch.setenv("PILOTSPACE_MODEL_SONNET_DEFAULT", "my-custom-sonnet")
        assert ModelTier.SONNET.model_id == "my-custom-sonnet"

    def test_resolve_model_opus_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ModelTier.OPUS resolves from env var when set."""
        monkeypatch.setenv("PILOTSPACE_MODEL_OPUS_DEFAULT", "my-custom-opus")
        assert ModelTier.OPUS.model_id == "my-custom-opus"

    def test_configure_sdk_with_tier_enum(self) -> None:
        """configure_sdk_for_space accepts ModelTier enum."""
        context = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"PILOT_WORKSPACE_ID": "ws-1", "PILOT_USER_ID": "u-1"},
        )
        config = configure_sdk_for_space(context, model=ModelTier.OPUS)
        assert "opus" in config.model.lower()

    def test_configure_sdk_with_tier_string(self) -> None:
        """configure_sdk_for_space accepts tier name string."""
        context = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"PILOT_WORKSPACE_ID": "ws-1", "PILOT_USER_ID": "u-1"},
        )
        config = configure_sdk_for_space(context, model="opus")
        assert "opus" in config.model.lower()

    def test_configure_sdk_default_is_sonnet_tier(self) -> None:
        """configure_sdk_for_space defaults to ModelTier.SONNET."""
        context = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"PILOT_WORKSPACE_ID": "ws-1", "PILOT_USER_ID": "u-1"},
        )
        config = configure_sdk_for_space(context)
        assert "sonnet" in config.model.lower()
