"""Unit tests for GhostTextService.

Tests caching, prompt construction, BYOK key resolution, ResilientExecutor
integration, CostTracker integration, and completion generation via Claude Haiku.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from anthropic.types import TextBlock

from pilot_space.ai.services.ghost_text import (
    _SYSTEM_PROMPT,
    GHOST_TEXT_CACHE_PREFIX,
    GHOST_TEXT_CACHE_TTL,
    MAX_TOKENS,
    TEMPERATURE,
    GhostTextService,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORKSPACE_ID: UUID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_ID: UUID = uuid4()
TEST_API_KEY = "sk-ant-test-workspace-key"  # pragma: allowlist secret


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Redis client stub with get/set/delete/scan_keys returning sane defaults."""
    redis = AsyncMock()
    redis.get.return_value = None  # cache miss by default
    redis.set.return_value = True
    redis.delete.return_value = True
    redis.scan_keys.return_value = []
    return redis


@pytest.fixture
def mock_executor() -> MagicMock:
    """ResilientExecutor stub."""
    executor = MagicMock()
    executor.execute = AsyncMock()
    return executor


@pytest.fixture
def mock_provider_selector() -> MagicMock:
    """ProviderSelector stub returning haiku model."""
    selector = MagicMock()
    selector.select.return_value = ("anthropic", "claude-3-5-haiku-20241022")
    return selector


@pytest.fixture
def mock_client_pool() -> MagicMock:
    """AnthropicClientPool stub."""
    pool = MagicMock()
    mock_client = AsyncMock()
    pool.get_client.return_value = mock_client
    return pool


@pytest.fixture
def mock_key_storage() -> AsyncMock:
    """SecureKeyStorage stub returning workspace key."""
    storage = AsyncMock()
    storage.get_api_key.return_value = TEST_API_KEY
    return storage


@pytest.fixture
def mock_cost_tracker() -> AsyncMock:
    """CostTracker stub."""
    return AsyncMock()


@pytest.fixture
def service(
    mock_redis: AsyncMock,
    mock_executor: MagicMock,
    mock_provider_selector: MagicMock,
    mock_client_pool: MagicMock,
    mock_key_storage: AsyncMock,
    mock_cost_tracker: AsyncMock,
) -> GhostTextService:
    """GhostTextService with all dependencies injected."""
    return GhostTextService(
        redis=mock_redis,
        resilient_executor=mock_executor,
        provider_selector=mock_provider_selector,
        client_pool=mock_client_pool,
        key_storage=mock_key_storage,
        cost_tracker=mock_cost_tracker,
    )


def _anthropic_response(text: str, stop_reason: str = "end_turn") -> MagicMock:
    """Build a minimal anthropic.Message mock with a real TextBlock.

    Using TextBlock (not MagicMock) so that isinstance(block, TextBlock)
    in the service's content extraction passes correctly.
    stop_reason controls the confidence heuristic branch under test.
    """
    msg = MagicMock()
    msg.content = [TextBlock(type="text", text=text)]
    msg.stop_reason = stop_reason
    msg.usage = MagicMock()
    msg.usage.input_tokens = 10
    msg.usage.output_tokens = 5
    return msg


# ---------------------------------------------------------------------------
# _build_cache_key
# ---------------------------------------------------------------------------


class TestBuildCacheKey:
    def test_includes_prefix_and_workspace(self) -> None:
        key = GhostTextService._build_cache_key("ctx", "prefix", WORKSPACE_ID)
        assert key.startswith(f"{GHOST_TEXT_CACHE_PREFIX}:{WORKSPACE_ID}:")

    def test_different_inputs_produce_different_keys(self) -> None:
        k1 = GhostTextService._build_cache_key("ctx", "a", WORKSPACE_ID)
        k2 = GhostTextService._build_cache_key("ctx", "b", WORKSPACE_ID)
        assert k1 != k2

    def test_same_inputs_produce_same_key(self) -> None:
        k1 = GhostTextService._build_cache_key("ctx", "prefix", WORKSPACE_ID)
        k2 = GhostTextService._build_cache_key("ctx", "prefix", WORKSPACE_ID)
        assert k1 == k2

    def test_different_workspaces_produce_different_keys(self) -> None:
        other_ws = uuid4()
        k1 = GhostTextService._build_cache_key("ctx", "prefix", WORKSPACE_ID)
        k2 = GhostTextService._build_cache_key("ctx", "prefix", other_ws)
        assert k1 != k2

    def test_hash_is_fixed_length(self) -> None:
        key = GhostTextService._build_cache_key("ctx", "prefix", WORKSPACE_ID)
        # key format: "ghost_text:{uuid}:{16-char-hash}"
        hash_part = key.split(":")[-1]
        assert len(hash_part) == 16

    def test_pipe_in_context_does_not_collide(self) -> None:
        """Length-prefix format must prevent separator injection collisions."""
        k1 = GhostTextService._build_cache_key("abc|", "def", WORKSPACE_ID)
        k2 = GhostTextService._build_cache_key("abc", "|def", WORKSPACE_ID)
        assert k1 != k2


# ---------------------------------------------------------------------------
# _build_prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    def test_includes_prefix(self) -> None:
        prompt = GhostTextService._build_prompt("", "def foo():")
        assert "def foo():" in prompt

    def test_includes_context_when_provided(self) -> None:
        prompt = GhostTextService._build_prompt("some context", "prefix")
        assert "some context" in prompt
        assert "prefix" in prompt

    def test_omits_context_section_when_empty(self) -> None:
        prompt = GhostTextService._build_prompt("", "prefix")
        assert "Context:" not in prompt
        assert "prefix" in prompt

    def test_context_and_prefix_separated(self) -> None:
        prompt = GhostTextService._build_prompt("context text", "start of line")
        assert "Context: context text" in prompt
        assert "Complete: start of line" in prompt


# ---------------------------------------------------------------------------
# generate_completion — cache hit
# ---------------------------------------------------------------------------


class TestGenerateCompletionCacheHit:
    @pytest.mark.asyncio
    async def test_returns_cached_result(
        self, service: GhostTextService, mock_redis: AsyncMock
    ) -> None:
        mock_redis.get.return_value = {"suggestion": "cached text", "confidence": 0.8}

        result = await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        assert result["suggestion"] == "cached text"
        assert result["confidence"] == 0.8
        assert result["cached"] is True

    @pytest.mark.asyncio
    async def test_does_not_call_executor_on_cache_hit(
        self, service: GhostTextService, mock_redis: AsyncMock, mock_executor: MagicMock
    ) -> None:
        mock_redis.get.return_value = {"suggestion": "cached", "confidence": 0.7}

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        mock_executor.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_cache_when_use_cache_false(
        self, service: GhostTextService, mock_redis: AsyncMock, mock_executor: MagicMock
    ) -> None:
        mock_redis.get.return_value = {"suggestion": "cached", "confidence": 0.9}
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("fresh completion"))

        result = await service.generate_completion(
            context="ctx",
            prefix="pre",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            use_cache=False,
        )

        assert result["cached"] is False
        assert result["suggestion"] == "fresh completion"


# ---------------------------------------------------------------------------
# generate_completion — API call via executor
# ---------------------------------------------------------------------------


class TestGenerateCompletionApiCall:
    @pytest.mark.asyncio
    async def test_returns_suggestion_from_executor(
        self, service: GhostTextService, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("a + b"))

        result = await service.generate_completion(
            context="def sum(a, b):",
            prefix="    return ",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
        )

        assert result["suggestion"] == "a + b"
        assert result["cached"] is False
        mock_executor.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_system_prompt_to_messages_create(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        """System prompt is forwarded inside the executor operation lambda."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=_anthropic_response("completion"))
        mock_client_pool.get_client.return_value = mock_client

        # Make executor actually invoke the operation lambda
        async def forward_operation(
            provider: str,
            operation: Any,
            timeout_sec: float | None = None,
            retry_config: Any = None,
        ) -> Any:
            return await operation()

        mock_executor.execute = AsyncMock(side_effect=forward_operation)

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        call_kwargs: dict[str, Any] = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == _SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_passes_correct_generation_params(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=_anthropic_response("completion"))
        mock_client_pool.get_client.return_value = mock_client

        async def forward_operation(
            provider: str,
            operation: Any,
            timeout_sec: float | None = None,
            retry_config: Any = None,
        ) -> Any:
            return await operation()

        mock_executor.execute = AsyncMock(side_effect=forward_operation)

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == MAX_TOKENS
        assert call_kwargs["temperature"] == TEMPERATURE

    @pytest.mark.asyncio
    async def test_model_resolved_from_provider_selector(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_provider_selector: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        """Model must come from ProviderSelector, not a hardcoded constant."""
        mock_provider_selector.select.return_value = ("anthropic", "claude-3-5-haiku-20241022")

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=_anthropic_response("ok"))
        mock_client_pool.get_client.return_value = mock_client

        async def forward_operation(
            provider: str,
            operation: Any,
            timeout_sec: float | None = None,
            retry_config: Any = None,
        ) -> Any:
            return await operation()

        mock_executor.execute = AsyncMock(side_effect=forward_operation)

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-3-5-haiku-20241022"

    @pytest.mark.asyncio
    async def test_stores_result_in_cache(
        self, service: GhostTextService, mock_redis: AsyncMock, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("stored result"))

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        mock_redis.set.assert_awaited_once()
        call_args = mock_redis.set.call_args
        assert call_args.kwargs.get("ttl") == GHOST_TEXT_CACHE_TTL
        cached_value: dict[str, Any] = call_args.args[1]
        assert cached_value["suggestion"] == "stored result"

    @pytest.mark.asyncio
    async def test_does_not_store_cache_when_use_cache_false(
        self, service: GhostTextService, mock_redis: AsyncMock, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("no cache"))

        await service.generate_completion(
            context="ctx",
            prefix="pre",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            use_cache=False,
        )

        mock_redis.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_confidence_capped_at_06_when_max_tokens(
        self, service: GhostTextService, mock_executor: MagicMock
    ) -> None:
        """Truncated completions (max_tokens) should report lower confidence."""
        mock_executor.execute = AsyncMock(
            return_value=_anthropic_response("x" * 200, stop_reason="max_tokens")
        )

        result = await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        assert result["confidence"] == 0.6

    @pytest.mark.asyncio
    async def test_confidence_uses_length_heuristic_on_end_turn(
        self, service: GhostTextService, mock_executor: MagicMock
    ) -> None:
        """Natural completions (end_turn) use length-based confidence, capped at 0.9."""
        mock_executor.execute = AsyncMock(
            return_value=_anthropic_response("x" * 200, stop_reason="end_turn")
        )

        result = await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_suggestion(
        self, service: GhostTextService, mock_executor: MagicMock
    ) -> None:
        response = MagicMock()
        response.content = []
        response.stop_reason = "end_turn"
        response.usage = MagicMock()
        response.usage.input_tokens = 5
        response.usage.output_tokens = 0
        mock_executor.execute = AsyncMock(return_value=response)

        result = await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        assert result["suggestion"] == ""

    @pytest.mark.asyncio
    async def test_api_exception_propagates(
        self, service: GhostTextService, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute = AsyncMock(side_effect=RuntimeError("API down"))

        with pytest.raises(RuntimeError, match="API down"):
            await service.generate_completion(
                context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
            )


# ---------------------------------------------------------------------------
# BYOK key resolution
# ---------------------------------------------------------------------------


class TestBYOKIntegration:
    @pytest.mark.asyncio
    async def test_workspace_key_fetched_from_key_storage(
        self,
        service: GhostTextService,
        mock_key_storage: AsyncMock,
        mock_executor: MagicMock,
    ) -> None:
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("ok"))

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        mock_key_storage.get_api_key.assert_awaited_once_with(WORKSPACE_ID, "anthropic", "llm")

    @pytest.mark.asyncio
    async def test_client_pool_called_with_workspace_key(
        self,
        service: GhostTextService,
        mock_client_pool: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("ok"))

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        mock_client_pool.get_client.assert_called_once_with(TEST_API_KEY)

    @pytest.mark.asyncio
    async def test_env_var_fallback_when_no_workspace_key(
        self,
        service: GhostTextService,
        mock_key_storage: AsyncMock,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        mock_key_storage.get_api_key.return_value = None
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("ok"))

        with patch("pilot_space.ai.services.ghost_text.get_settings") as mock_cfg:
            mock_settings = MagicMock()
            mock_settings.anthropic_api_key = MagicMock()
            mock_settings.anthropic_api_key.get_secret_value.return_value = "sk-ant-env-key"
            mock_cfg.return_value = mock_settings

            await service.generate_completion(
                context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
            )

        mock_client_pool.get_client.assert_called_once_with("sk-ant-env-key")

    @pytest.mark.asyncio
    async def test_raises_402_when_no_key_available(
        self,
        service: GhostTextService,
        mock_key_storage: AsyncMock,
    ) -> None:
        from fastapi import HTTPException

        mock_key_storage.get_api_key.return_value = None

        with patch("pilot_space.ai.services.ghost_text.get_settings") as mock_cfg:
            mock_settings = MagicMock()
            mock_settings.anthropic_api_key = None
            mock_cfg.return_value = mock_settings

            with pytest.raises(HTTPException) as exc_info:
                await service.generate_completion(
                    context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
                )

        assert exc_info.value.status_code == 402


# ---------------------------------------------------------------------------
# ResilientExecutor integration
# ---------------------------------------------------------------------------


class TestResilientExecutorIntegration:
    @pytest.mark.asyncio
    async def test_executor_called_with_anthropic_provider(
        self, service: GhostTextService, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("ok"))

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        call_kwargs = mock_executor.execute.call_args.kwargs
        assert call_kwargs["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_executor_called_with_timeout_2_5s(
        self, service: GhostTextService, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("ok"))

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        call_kwargs = mock_executor.execute.call_args.kwargs
        assert call_kwargs["timeout_sec"] == 2.5


# ---------------------------------------------------------------------------
# CostTracker integration
# ---------------------------------------------------------------------------


class TestCostTrackerIntegration:
    @pytest.mark.asyncio
    async def test_cost_tracker_called_after_completion(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_cost_tracker: AsyncMock,
    ) -> None:
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("ok"))

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        mock_cost_tracker.track.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cost_tracker_receives_correct_attribution(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_cost_tracker: AsyncMock,
    ) -> None:
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("ok"))

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        kwargs = mock_cost_tracker.track.call_args.kwargs
        assert kwargs["workspace_id"] == WORKSPACE_ID
        assert kwargs["user_id"] == TEST_USER_ID
        assert kwargs["agent_name"] == "ghost_text"
        assert kwargs["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_cost_tracker_failure_does_not_fail_completion(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_cost_tracker: AsyncMock,
    ) -> None:
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("ok"))
        mock_cost_tracker.track = AsyncMock(side_effect=RuntimeError("DB unavailable"))

        result = await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        assert result["suggestion"] == "ok"

    @pytest.mark.asyncio
    async def test_cost_tracker_not_called_on_cache_hit(
        self,
        service: GhostTextService,
        mock_redis: AsyncMock,
        mock_cost_tracker: AsyncMock,
    ) -> None:
        mock_redis.get.return_value = {"suggestion": "cached", "confidence": 0.8}

        await service.generate_completion(
            context="ctx", prefix="pre", workspace_id=WORKSPACE_ID, user_id=TEST_USER_ID
        )

        mock_cost_tracker.track.assert_not_awaited()


# ---------------------------------------------------------------------------
# clear_workspace_cache
# ---------------------------------------------------------------------------


class TestClearWorkspaceCache:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_keys(
        self, service: GhostTextService, mock_redis: AsyncMock
    ) -> None:
        mock_redis.scan_keys.return_value = []
        count = await service.clear_workspace_cache(WORKSPACE_ID)
        assert count == 0

    @pytest.mark.asyncio
    async def test_deletes_all_matching_keys(
        self, service: GhostTextService, mock_redis: AsyncMock
    ) -> None:
        keys = [
            f"{GHOST_TEXT_CACHE_PREFIX}:{WORKSPACE_ID}:aaa",
            f"{GHOST_TEXT_CACHE_PREFIX}:{WORKSPACE_ID}:bbb",
            f"{GHOST_TEXT_CACHE_PREFIX}:{WORKSPACE_ID}:ccc",
        ]
        mock_redis.scan_keys.return_value = keys

        count = await service.clear_workspace_cache(WORKSPACE_ID)

        assert count == 3
        mock_redis.delete.assert_awaited_once_with(*keys)

    @pytest.mark.asyncio
    async def test_scans_correct_pattern(
        self, service: GhostTextService, mock_redis: AsyncMock
    ) -> None:
        await service.clear_workspace_cache(WORKSPACE_ID)

        mock_redis.scan_keys.assert_awaited_once_with(
            f"{GHOST_TEXT_CACHE_PREFIX}:{WORKSPACE_ID}:*",
            max_keys=1000,
        )
