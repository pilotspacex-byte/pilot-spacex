"""Unit tests for GhostTextService proxy routing.

Tests that GhostTextService routes through the built-in HTTP proxy when
ai_proxy_enabled=True and preserves direct SDK path when disabled.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from anthropic.types import TextBlock

from pilot_space.ai.services.ghost_text import GhostTextService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKSPACE_ID: UUID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_ID: UUID = uuid4()
TEST_API_KEY = "sk-ant-test-workspace-key"  # pragma: allowlist secret
PROXY_BASE_URL = "http://localhost:8000/api/v1/ai/proxy"
BYOK_BASE_URL = "https://custom-proxy.example.com/v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _anthropic_response(text: str = "completion", stop_reason: str = "end_turn") -> MagicMock:
    """Build a minimal anthropic.Message mock with a real TextBlock."""
    msg = MagicMock()
    msg.content = [TextBlock(type="text", text=text)]
    msg.stop_reason = stop_reason
    msg.usage = MagicMock()
    msg.usage.input_tokens = 10
    msg.usage.output_tokens = 5
    return msg


def _make_settings(proxy_enabled: bool = False) -> MagicMock:
    """Build a mock Settings object with proxy config."""
    settings = MagicMock()
    settings.ai_proxy_enabled = proxy_enabled
    settings.ai_proxy_base_url = PROXY_BASE_URL
    settings.anthropic_api_key = MagicMock()
    settings.anthropic_api_key.get_secret_value.return_value = (
        "sk-env-key"  # pragma: allowlist secret
    )
    return settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.get.return_value = None
    redis.set.return_value = True
    return redis


@pytest.fixture
def mock_executor() -> MagicMock:
    executor = MagicMock()
    executor.execute = AsyncMock(return_value=_anthropic_response())
    return executor


@pytest.fixture
def mock_provider_selector() -> MagicMock:
    selector = MagicMock()
    selector.select.return_value = ("anthropic", "claude-3-5-haiku-20241022")
    return selector


@pytest.fixture
def mock_client_pool() -> MagicMock:
    pool = MagicMock()
    pool.get_client.return_value = AsyncMock()
    return pool


@pytest.fixture
def mock_key_storage() -> AsyncMock:
    storage = AsyncMock()
    storage.get_api_key.return_value = TEST_API_KEY
    mock_key_info = MagicMock()
    mock_key_info.base_url = None
    mock_key_info.model_name = None
    storage.get_key_info.return_value = mock_key_info
    storage.get_all_key_infos.return_value = []
    storage.db = None  # skip DB settings lookup in _resolve_workspace_provider
    return storage


@pytest.fixture
def mock_cost_tracker() -> AsyncMock:
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
    return GhostTextService(
        redis=mock_redis,
        resilient_executor=mock_executor,
        provider_selector=mock_provider_selector,
        client_pool=mock_client_pool,
        key_storage=mock_key_storage,
        cost_tracker=mock_cost_tracker,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_proxy_enabled_uses_proxy_base_url(
    service: GhostTextService,
    mock_client_pool: MagicMock,
) -> None:
    """When ai_proxy_enabled=True, get_client receives proxy base_url."""
    with patch(
        "pilot_space.ai.services.ghost_text.get_settings",
        return_value=_make_settings(proxy_enabled=True),
    ):
        await service.generate_completion(
            context="def foo():",
            prefix="    return ",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            use_cache=False,
        )

    # client_pool.get_client should have been called with proxy base_url (workspace_id in path)
    mock_client_pool.get_client.assert_called_once()
    call_kwargs = mock_client_pool.get_client.call_args
    assert call_kwargs[1]["base_url"] == f"{PROXY_BASE_URL}/{WORKSPACE_ID}/"


@pytest.mark.asyncio
async def test_proxy_enabled_skips_cost_tracking(
    service: GhostTextService,
    mock_cost_tracker: AsyncMock,
) -> None:
    """When ai_proxy_enabled=True, cost_tracker.track() is NOT called."""
    with patch(
        "pilot_space.ai.services.ghost_text.get_settings",
        return_value=_make_settings(proxy_enabled=True),
    ):
        await service.generate_completion(
            context="def foo():",
            prefix="    return ",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            use_cache=False,
        )

    mock_cost_tracker.track.assert_not_called()


@pytest.mark.asyncio
async def test_proxy_disabled_uses_byok_base_url_and_tracks_cost(
    service: GhostTextService,
    mock_client_pool: MagicMock,
    mock_key_storage: AsyncMock,
    mock_cost_tracker: AsyncMock,
) -> None:
    """When ai_proxy_enabled=False, original BYOK base_url is used and cost is tracked."""
    # Set up BYOK key_info with custom base_url
    key_info = MagicMock()
    key_info.base_url = BYOK_BASE_URL
    mock_key_storage.get_key_info.return_value = key_info

    with patch(
        "pilot_space.ai.services.ghost_text.get_settings",
        return_value=_make_settings(proxy_enabled=False),
    ):
        await service.generate_completion(
            context="def foo():",
            prefix="    return ",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            use_cache=False,
        )

    # Should use BYOK base_url, not proxy
    call_kwargs = mock_client_pool.get_client.call_args
    assert call_kwargs[1]["base_url"] == BYOK_BASE_URL

    # Cost tracking should happen
    mock_cost_tracker.track.assert_called_once()


@pytest.mark.asyncio
async def test_proxy_enabled_no_byok_key_uses_env_key_and_proxy(
    mock_redis: AsyncMock,
    mock_executor: MagicMock,
    mock_provider_selector: MagicMock,
    mock_client_pool: MagicMock,
    mock_cost_tracker: AsyncMock,
) -> None:
    """When ai_proxy_enabled=True but no BYOK key, falls back to env key with proxy base_url."""
    # key_storage returns no workspace key
    key_storage = AsyncMock()
    key_storage.get_api_key.return_value = None
    key_storage.get_key_info.return_value = None
    key_storage.get_all_key_infos.return_value = []
    key_storage.db = None

    service = GhostTextService(
        redis=mock_redis,
        resilient_executor=mock_executor,
        provider_selector=mock_provider_selector,
        client_pool=mock_client_pool,
        key_storage=key_storage,
        cost_tracker=mock_cost_tracker,
    )

    with patch(
        "pilot_space.ai.services.ghost_text.get_settings",
        return_value=_make_settings(proxy_enabled=True),
    ):
        await service.generate_completion(
            context="def foo():",
            prefix="    return ",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            use_cache=False,
        )

    # Should still use proxy base_url (workspace_id in path) even with env fallback key
    call_kwargs = mock_client_pool.get_client.call_args
    assert call_kwargs[1]["base_url"] == f"{PROXY_BASE_URL}/{WORKSPACE_ID}/"
