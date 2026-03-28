"""Unit tests for LLMGateway proxy routing.

Tests that LLMGateway.complete() and embed() route through the built-in
AI proxy when ai_proxy_enabled=True, and skip local cost tracking when proxied.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.infrastructure.key_storage import APIKeyInfo
from pilot_space.ai.providers.provider_selector import TaskType
from pilot_space.ai.proxy.llm_gateway import LLMGateway, LLMResponse

# -- Helpers -------------------------------------------------------------------


def _make_anthropic_response(
    text: str = "proxied response",
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def _make_openai_response(
    text: str = "proxied response",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


def _make_embedding_response(
    embeddings: list[list[float]] | None = None,
    total_tokens: int = 10,
) -> SimpleNamespace:
    if embeddings is None:
        embeddings = [[0.1, 0.2, 0.3]]
    return SimpleNamespace(
        data=[SimpleNamespace(embedding=e) for e in embeddings],
        usage=SimpleNamespace(total_tokens=total_tokens),
    )


def _make_key_info(base_url: str | None = None) -> APIKeyInfo:
    from datetime import UTC, datetime

    return APIKeyInfo(
        workspace_id=WS_ID,
        provider="anthropic",
        service_type="llm",
        is_valid=True,
        last_validated_at=datetime.now(UTC),
        validation_error=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        base_url=base_url,
    )


WS_ID = uuid4()
USER_ID = uuid4()
PROXY_BASE_URL = "http://localhost:8000/api/v1/ai/proxy"


# -- Fixtures ------------------------------------------------------------------


@pytest.fixture
def mock_executor() -> AsyncMock:
    executor = AsyncMock()

    async def _pass_through(provider: str, operation: object, **kwargs: object) -> object:
        return await operation()  # type: ignore[misc]

    executor.execute = AsyncMock(side_effect=_pass_through)
    return executor


@pytest.fixture
def mock_cost_tracker() -> AsyncMock:
    tracker = AsyncMock()
    tracker.track = AsyncMock()
    return tracker


@pytest.fixture
def mock_key_storage() -> AsyncMock:
    storage = AsyncMock()
    storage.get_api_key = AsyncMock(return_value="sk-test-key")
    storage.get_key_info = AsyncMock(return_value=None)
    return storage


@pytest.fixture
def gateway(
    mock_executor: AsyncMock,
    mock_cost_tracker: AsyncMock,
    mock_key_storage: AsyncMock,
) -> LLMGateway:
    return LLMGateway(mock_executor, mock_cost_tracker, mock_key_storage)


def _mock_settings(ai_proxy_enabled: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        ai_proxy_enabled=ai_proxy_enabled,
        ai_proxy_base_url=PROXY_BASE_URL,
    )


# -- Test 1: Proxy routing for Anthropic complete() ---------------------------


@patch("pilot_space.ai.proxy.llm_gateway.get_settings")
@patch("pilot_space.ai.proxy.llm_gateway.anthropic")
async def test_complete_anthropic_routes_through_proxy_when_enabled(
    mock_anthropic_mod: MagicMock,
    mock_get_settings: MagicMock,
    gateway: LLMGateway,
    mock_key_storage: AsyncMock,
) -> None:
    """When ai_proxy_enabled=True, complete() uses proxy base_url with workspace_id in path."""
    mock_get_settings.return_value = _mock_settings(ai_proxy_enabled=True)

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_make_anthropic_response())
    mock_anthropic_mod.AsyncAnthropic.return_value = mock_client
    gateway._anthropic_clients.clear()

    result = await gateway.complete(
        workspace_id=WS_ID,
        user_id=USER_ID,
        task_type=TaskType.PR_REVIEW,
        messages=[{"role": "user", "content": "review this"}],
    )

    assert isinstance(result, LLMResponse)
    # Verify client created with proxy base_url containing workspace_id, no custom headers
    call_kwargs = mock_anthropic_mod.AsyncAnthropic.call_args.kwargs
    assert call_kwargs["base_url"] == f"{PROXY_BASE_URL}/{WS_ID}/"
    assert "default_headers" not in call_kwargs


# -- Test 2: Proxy skips local cost tracking -----------------------------------


@patch("pilot_space.ai.proxy.llm_gateway.get_settings")
@patch("pilot_space.ai.proxy.llm_gateway.track_llm_cost")
async def test_complete_anthropic_skips_cost_tracking_when_proxied(
    mock_track_cost: AsyncMock,
    mock_get_settings: MagicMock,
    gateway: LLMGateway,
) -> None:
    """When ai_proxy_enabled=True, complete() skips track_llm_cost (proxy handles it)."""
    mock_get_settings.return_value = _mock_settings(ai_proxy_enabled=True)

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_make_anthropic_response())
    gateway._get_anthropic_client = MagicMock(return_value=mock_client)  # type: ignore[method-assign]

    await gateway.complete(
        workspace_id=WS_ID,
        user_id=USER_ID,
        task_type=TaskType.PR_REVIEW,
        messages=[{"role": "user", "content": "review"}],
    )

    mock_track_cost.assert_not_called()


# -- Test 3: Non-proxy preserves original behavior ----------------------------


@patch("pilot_space.ai.proxy.llm_gateway.get_settings")
@patch("pilot_space.ai.proxy.llm_gateway.track_llm_cost")
@patch("pilot_space.ai.proxy.llm_gateway.anthropic")
async def test_complete_anthropic_uses_byok_when_proxy_disabled(
    mock_anthropic_mod: MagicMock,
    mock_track_cost: AsyncMock,
    mock_get_settings: MagicMock,
    gateway: LLMGateway,
    mock_key_storage: AsyncMock,
) -> None:
    """When ai_proxy_enabled=False, complete() uses BYOK base_url and tracks cost locally."""
    mock_get_settings.return_value = _mock_settings(ai_proxy_enabled=False)
    mock_key_storage.get_key_info = AsyncMock(
        return_value=_make_key_info(base_url="https://byok.example.com")
    )

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_make_anthropic_response())
    mock_anthropic_mod.AsyncAnthropic.return_value = mock_client
    gateway._anthropic_clients.clear()

    await gateway.complete(
        workspace_id=WS_ID,
        user_id=USER_ID,
        task_type=TaskType.PR_REVIEW,
        messages=[{"role": "user", "content": "review"}],
    )

    # Verify client uses BYOK base_url, NOT proxy
    call_kwargs = mock_anthropic_mod.AsyncAnthropic.call_args.kwargs
    assert call_kwargs["base_url"] == "https://byok.example.com"
    assert "default_headers" not in call_kwargs

    # Cost tracking should be called locally
    mock_track_cost.assert_called_once()


# -- Test 4: Proxy routing for embed() ----------------------------------------


@patch("pilot_space.ai.proxy.llm_gateway.get_settings")
@patch("pilot_space.ai.proxy.llm_gateway.openai")
async def test_embed_routes_through_proxy_when_enabled(
    mock_openai_mod: MagicMock,
    mock_get_settings: MagicMock,
    gateway: LLMGateway,
    mock_key_storage: AsyncMock,
) -> None:
    """When ai_proxy_enabled=True, embed() uses proxy base_url with workspace_id in path."""
    mock_get_settings.return_value = _mock_settings(ai_proxy_enabled=True)

    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=_make_embedding_response())
    mock_openai_mod.AsyncOpenAI.return_value = mock_client
    gateway._openai_clients.clear()

    await gateway.embed(
        workspace_id=WS_ID,
        user_id=USER_ID,
        texts=["hello"],
    )

    call_kwargs = mock_openai_mod.AsyncOpenAI.call_args.kwargs
    assert call_kwargs["base_url"] == f"{PROXY_BASE_URL}/{WS_ID}/"
    assert "default_headers" not in call_kwargs


# -- Test 5: embed() skips cost tracking when proxied -------------------------


@patch("pilot_space.ai.proxy.llm_gateway.get_settings")
@patch("pilot_space.ai.proxy.llm_gateway.track_llm_cost")
async def test_embed_skips_cost_tracking_when_proxied(
    mock_track_cost: AsyncMock,
    mock_get_settings: MagicMock,
    gateway: LLMGateway,
) -> None:
    """When ai_proxy_enabled=True, embed() skips track_llm_cost."""
    mock_get_settings.return_value = _mock_settings(ai_proxy_enabled=True)

    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=_make_embedding_response())
    gateway._get_openai_client = MagicMock(return_value=mock_client)  # type: ignore[method-assign]

    await gateway.embed(
        workspace_id=WS_ID,
        user_id=USER_ID,
        texts=["hello"],
    )

    mock_track_cost.assert_not_called()


# -- Test 6: embed() non-proxy preserves original behavior --------------------


@patch("pilot_space.ai.proxy.llm_gateway.get_settings")
@patch("pilot_space.ai.proxy.llm_gateway.track_llm_cost")
@patch("pilot_space.ai.proxy.llm_gateway.openai")
async def test_embed_uses_byok_when_proxy_disabled(
    mock_openai_mod: MagicMock,
    mock_track_cost: AsyncMock,
    mock_get_settings: MagicMock,
    gateway: LLMGateway,
    mock_key_storage: AsyncMock,
) -> None:
    """When ai_proxy_enabled=False, embed() uses BYOK base_url and tracks cost locally."""
    mock_get_settings.return_value = _mock_settings(ai_proxy_enabled=False)
    mock_key_storage.get_key_info = AsyncMock(
        return_value=_make_key_info(base_url="https://embed-byok.example.com")
    )

    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=_make_embedding_response())
    mock_openai_mod.AsyncOpenAI.return_value = mock_client
    gateway._openai_clients.clear()

    await gateway.embed(
        workspace_id=WS_ID,
        user_id=USER_ID,
        texts=["hello"],
    )

    call_kwargs = mock_openai_mod.AsyncOpenAI.call_args.kwargs
    assert call_kwargs["base_url"] == "https://embed-byok.example.com"
    assert "default_headers" not in call_kwargs

    mock_track_cost.assert_called_once()
