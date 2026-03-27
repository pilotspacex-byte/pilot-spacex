"""Unit tests for EmbeddingService.

Tests provider cascade: LLMGateway → Ollama, failure isolation, and edge cases.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from pilot_space.ai.proxy.llm_gateway import EmbeddingResponse
from pilot_space.application.services.embedding_service import (
    EmbeddingConfig,
    EmbeddingService,
)

_WORKSPACE_ID = UUID("11111111-1111-1111-1111-111111111111")
_USER_ID = UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def mock_llm_gateway() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def gateway_config() -> EmbeddingConfig:
    return EmbeddingConfig()


@pytest.fixture
def no_key_config() -> EmbeddingConfig:
    return EmbeddingConfig()


@pytest.fixture
def ollama_only_config() -> EmbeddingConfig:
    return EmbeddingConfig(ollama_base_url="http://localhost:11434")


@pytest.mark.asyncio
async def test_openai_success_no_ollama_called(
    gateway_config: EmbeddingConfig, mock_llm_gateway: AsyncMock
) -> None:
    """LLMGateway success → return immediately, Ollama NOT called."""
    vector = [0.1] * 768
    mock_llm_gateway.embed.return_value = EmbeddingResponse(
        embeddings=[vector], model="openai/text-embedding-3-large", input_tokens=10
    )
    ollama_mock = AsyncMock(return_value=None)

    with patch.object(EmbeddingService, "_embed_ollama", ollama_mock):
        svc = EmbeddingService(gateway_config, llm_gateway=mock_llm_gateway)
        result = await svc.embed("hello world", workspace_id=_WORKSPACE_ID, user_id=_USER_ID)

    assert result == vector
    ollama_mock.assert_not_called()


@pytest.mark.asyncio
async def test_openai_failure_falls_back_to_ollama(
    gateway_config: EmbeddingConfig, mock_llm_gateway: AsyncMock
) -> None:
    """LLMGateway raises → Ollama called as fallback."""
    vector = [0.2] * 768
    mock_llm_gateway.embed.side_effect = Exception("Gateway error")

    with patch.object(EmbeddingService, "_embed_ollama", new=AsyncMock(return_value=vector)):
        svc = EmbeddingService(gateway_config, llm_gateway=mock_llm_gateway)
        result = await svc.embed("hello world", workspace_id=_WORKSPACE_ID, user_id=_USER_ID)

    assert result == vector


@pytest.mark.asyncio
async def test_both_fail_returns_none(
    gateway_config: EmbeddingConfig, mock_llm_gateway: AsyncMock
) -> None:
    """Both LLMGateway and Ollama fail → returns None."""
    mock_llm_gateway.embed.side_effect = Exception("Gateway error")

    with patch.object(EmbeddingService, "_embed_ollama", new=AsyncMock(return_value=None)):
        svc = EmbeddingService(gateway_config, llm_gateway=mock_llm_gateway)
        result = await svc.embed("hello world", workspace_id=_WORKSPACE_ID, user_id=_USER_ID)

    assert result is None


@pytest.mark.asyncio
async def test_empty_text_returns_none(
    gateway_config: EmbeddingConfig, mock_llm_gateway: AsyncMock
) -> None:
    """Empty string → None without calling any provider."""
    svc = EmbeddingService(gateway_config, llm_gateway=mock_llm_gateway)
    result = await svc.embed("")

    assert result is None
    mock_llm_gateway.embed.assert_not_called()


@pytest.mark.asyncio
async def test_whitespace_only_text_returns_none(
    gateway_config: EmbeddingConfig, mock_llm_gateway: AsyncMock
) -> None:
    """Whitespace-only string → None."""
    svc = EmbeddingService(gateway_config, llm_gateway=mock_llm_gateway)
    result = await svc.embed("   \n\t  ")
    assert result is None


@pytest.mark.asyncio
async def test_no_gateway_skips_to_ollama(no_key_config: EmbeddingConfig) -> None:
    """No LLMGateway → skips gateway, tries Ollama directly."""
    vector = [0.3] * 768

    with patch(
        "pilot_space.application.services.embedding_service.asyncio.to_thread",
        new=AsyncMock(return_value=vector),
    ):
        svc = EmbeddingService(no_key_config)
        result = await svc.embed("test text", workspace_id=_WORKSPACE_ID, user_id=_USER_ID)

    assert result == vector


@pytest.mark.asyncio
async def test_no_gateway_ollama_also_fails_returns_none(no_key_config: EmbeddingConfig) -> None:
    """No gateway, Ollama fails → returns None."""
    with patch(
        "pilot_space.application.services.embedding_service.asyncio.to_thread",
        side_effect=Exception("Ollama down"),
    ):
        svc = EmbeddingService(no_key_config)
        result = await svc.embed("test text", workspace_id=_WORKSPACE_ID, user_id=_USER_ID)

    assert result is None


@pytest.mark.asyncio
async def test_768_dim_output(gateway_config: EmbeddingConfig, mock_llm_gateway: AsyncMock) -> None:
    """Validates that returned vector has 768 dimensions."""
    vector = [float(i) / 768 for i in range(768)]
    mock_llm_gateway.embed.return_value = EmbeddingResponse(
        embeddings=[vector], model="openai/text-embedding-3-large", input_tokens=5
    )

    svc = EmbeddingService(gateway_config, llm_gateway=mock_llm_gateway)
    result = await svc.embed("test", workspace_id=_WORKSPACE_ID, user_id=_USER_ID)

    assert result is not None
    assert len(result) == 768


@pytest.mark.asyncio
async def test_timeout_falls_back_to_ollama(
    gateway_config: EmbeddingConfig, mock_llm_gateway: AsyncMock
) -> None:
    """TimeoutError from LLMGateway → Ollama fallback."""
    vector = [0.4] * 768
    mock_llm_gateway.embed.side_effect = TimeoutError("Gateway timeout")

    with patch.object(EmbeddingService, "_embed_ollama", new=AsyncMock(return_value=vector)):
        svc = EmbeddingService(gateway_config, llm_gateway=mock_llm_gateway)
        result = await svc.embed("test query", workspace_id=_WORKSPACE_ID, user_id=_USER_ID)

    assert result == vector
