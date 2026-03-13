"""Unit tests for EmbeddingService.

Tests provider cascade: OpenAI → Ollama, failure isolation, and edge cases.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.application.services.embedding_service import (
    EmbeddingConfig,
    EmbeddingService,
    _ollama_embed_sync,
)


@pytest.fixture
def openai_config() -> EmbeddingConfig:
    return EmbeddingConfig(openai_api_key="sk-test-key")  # pragma: allowlist secret


@pytest.fixture
def no_key_config() -> EmbeddingConfig:
    return EmbeddingConfig()


@pytest.fixture
def ollama_only_config() -> EmbeddingConfig:
    return EmbeddingConfig(ollama_base_url="http://localhost:11434")


@pytest.mark.asyncio
async def test_openai_success_no_ollama_called(openai_config: EmbeddingConfig) -> None:
    """OpenAI success → return immediately, Ollama NOT called."""
    vector = [0.1] * 768
    ollama_mock = AsyncMock(return_value=None)

    with (
        patch.object(EmbeddingService, "_embed_openai", new=AsyncMock(return_value=vector)),
        patch.object(EmbeddingService, "_embed_ollama", ollama_mock),
    ):
        svc = EmbeddingService(openai_config)
        result = await svc.embed("hello world")

    assert result == vector
    ollama_mock.assert_not_called()


@pytest.mark.asyncio
async def test_openai_failure_falls_back_to_ollama(openai_config: EmbeddingConfig) -> None:
    """OpenAI raises → Ollama called as fallback."""
    vector = [0.2] * 768

    with (
        patch.object(EmbeddingService, "_embed_openai", new=AsyncMock(return_value=None)),
        patch.object(EmbeddingService, "_embed_ollama", new=AsyncMock(return_value=vector)),
    ):
        svc = EmbeddingService(openai_config)
        result = await svc.embed("hello world")

    assert result == vector


@pytest.mark.asyncio
async def test_both_fail_returns_none(openai_config: EmbeddingConfig) -> None:
    """Both OpenAI and Ollama fail → returns None."""
    with (
        patch.object(EmbeddingService, "_embed_openai", new=AsyncMock(return_value=None)),
        patch.object(EmbeddingService, "_embed_ollama", new=AsyncMock(return_value=None)),
    ):
        svc = EmbeddingService(openai_config)
        result = await svc.embed("hello world")

    assert result is None


@pytest.mark.asyncio
async def test_empty_text_returns_none(openai_config: EmbeddingConfig) -> None:
    """Empty string → None without calling any provider."""
    with patch("pilot_space.application.services.embedding_service.asyncio.wait_for") as mock_wait:
        svc = EmbeddingService(openai_config)
        result = await svc.embed("")

    assert result is None
    mock_wait.assert_not_called()


@pytest.mark.asyncio
async def test_whitespace_only_text_returns_none(openai_config: EmbeddingConfig) -> None:
    """Whitespace-only string → None."""
    svc = EmbeddingService(openai_config)
    result = await svc.embed("   \n\t  ")
    assert result is None


@pytest.mark.asyncio
async def test_no_api_key_skips_openai_goes_to_ollama(no_key_config: EmbeddingConfig) -> None:
    """No OpenAI key → skips OpenAI, tries Ollama directly."""
    vector = [0.3] * 768

    with (
        patch("pilot_space.application.services.embedding_service.asyncio.wait_for") as mock_wait,
        patch(
            "pilot_space.application.services.embedding_service.asyncio.to_thread",
            new=AsyncMock(return_value=vector),
        ),
    ):
        svc = EmbeddingService(no_key_config)
        result = await svc.embed("test text")

    assert result == vector
    mock_wait.assert_not_called()


@pytest.mark.asyncio
async def test_no_key_ollama_also_fails_returns_none(no_key_config: EmbeddingConfig) -> None:
    """No key, Ollama fails → returns None."""
    with patch(
        "pilot_space.application.services.embedding_service.asyncio.to_thread",
        side_effect=Exception("Ollama down"),
    ):
        svc = EmbeddingService(no_key_config)
        result = await svc.embed("test text")

    assert result is None


@pytest.mark.asyncio
async def test_768_dim_output(openai_config: EmbeddingConfig) -> None:
    """Validates that returned vector has 768 dimensions."""
    vector = [float(i) / 768 for i in range(768)]

    with patch.object(EmbeddingService, "_embed_openai", new=AsyncMock(return_value=vector)):
        svc = EmbeddingService(openai_config)
        result = await svc.embed("test")

    assert result is not None
    assert len(result) == 768


@pytest.mark.asyncio
async def test_timeout_falls_back_to_ollama(openai_config: EmbeddingConfig) -> None:
    """TimeoutError from OpenAI → Ollama fallback."""
    vector = [0.4] * 768

    with (
        patch.object(EmbeddingService, "_embed_openai", new=AsyncMock(return_value=None)),
        patch.object(EmbeddingService, "_embed_ollama", new=AsyncMock(return_value=vector)),
    ):
        svc = EmbeddingService(openai_config)
        result = await svc.embed("test query")

    assert result == vector


# ---------------------------------------------------------------------------
# _embed_openai implementation tests (lines 87-110)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_openai_success_extracts_embedding(openai_config: EmbeddingConfig) -> None:
    """_embed_openai extracts embedding from OpenAI response object."""
    vector = [0.1] * 768

    svc = EmbeddingService(openai_config)

    # Build a fake response matching OpenAI's CreateEmbeddingResponse shape.
    embedding_obj = MagicMock()
    embedding_obj.embedding = vector
    response = MagicMock()
    response.data = [embedding_obj]

    # Mock the client method to return the fake response as an awaitable.
    svc._openai_client.embeddings.create = AsyncMock(return_value=response)  # type: ignore[union-attr]

    result = await svc._embed_openai("test")

    assert result == vector
    assert len(result) == 768  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_embed_openai_timeout_returns_none(openai_config: EmbeddingConfig) -> None:
    """_embed_openai returns None when asyncio.wait_for raises TimeoutError."""
    svc = EmbeddingService(openai_config)

    with patch(
        "pilot_space.application.services.embedding_service.asyncio.wait_for",
        side_effect=TimeoutError,
    ):
        result = await svc._embed_openai("test")

    assert result is None


@pytest.mark.asyncio
async def test_embed_openai_generic_exception_returns_none(openai_config: EmbeddingConfig) -> None:
    """_embed_openai returns None on arbitrary exceptions."""
    svc = EmbeddingService(openai_config)

    with patch(
        "pilot_space.application.services.embedding_service.asyncio.wait_for",
        side_effect=RuntimeError("API error"),
    ):
        result = await svc._embed_openai("test")

    assert result is None


# ---------------------------------------------------------------------------
# _ollama_embed_sync implementation tests (lines 130-150)
# ---------------------------------------------------------------------------


def test_ollama_embed_sync_success() -> None:
    """_ollama_embed_sync returns embedding list on valid response."""
    import json

    vector = [0.1] * 768
    response_body = json.dumps({"embeddings": [vector]}).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = response_body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = _ollama_embed_sync("test", "http://localhost:11434", "model", 30)

    assert result == vector
    assert len(result) == 768  # type: ignore[arg-type]


def test_ollama_embed_sync_empty_embeddings_returns_none() -> None:
    """_ollama_embed_sync returns None when embeddings list is empty."""
    import json

    response_body = json.dumps({"embeddings": []}).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = response_body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = _ollama_embed_sync("test", "http://localhost:11434", "model", 30)

    assert result is None


def test_ollama_embed_sync_missing_key_returns_none() -> None:
    """_ollama_embed_sync returns None when response has no 'embeddings' key."""
    import json

    response_body = json.dumps({}).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = response_body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = _ollama_embed_sync("test", "http://localhost:11434", "model", 30)

    assert result is None
