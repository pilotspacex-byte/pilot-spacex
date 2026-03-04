"""Unit tests for MemoryEmbeddingJobHandler.handle_graph_node.

Covers:
- Early return when openai_api_key is None
- Missing node_id in payload
- Missing workspace_id in payload
- Node not found in DB
- Happy path: embedding stored, success result returned
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.infrastructure.queue.handlers.memory_embedding_handler import (
    MemoryEmbeddingJobHandler,
)

pytestmark = pytest.mark.asyncio

_NODE_ID = uuid4()
_WORKSPACE_ID = uuid4()


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


def _make_handler(
    session: AsyncMock,
    openai_api_key: str | None = "sk-test",  # pragma: allowlist secret
) -> MemoryEmbeddingJobHandler:
    return MemoryEmbeddingJobHandler(
        session=session,
        google_api_key=None,
        openai_api_key=openai_api_key,
    )


class TestHandleGraphNodeEarlyReturns:
    """Guard clause tests — no DB calls should be made."""

    async def test_returns_error_when_all_providers_fail(self) -> None:
        """When both OpenAI (no key) and Ollama fail, error is returned."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.first.return_value = ("Node content text.",)
        session.execute = AsyncMock(return_value=mock_result)
        handler = _make_handler(session, openai_api_key=None)

        with patch(
            "pilot_space.infrastructure.queue.handlers.memory_embedding_handler._embed_text_ollama",
            new=AsyncMock(return_value=None),
        ):
            result = await handler.handle_graph_node(
                {"node_id": str(_NODE_ID), "workspace_id": str(_WORKSPACE_ID)}
            )

        assert result["success"] is False
        assert "all embedding providers failed" in result["error"]

    async def test_returns_error_when_node_id_missing(self) -> None:
        session = _make_session()
        handler = _make_handler(session)

        result = await handler.handle_graph_node({"workspace_id": str(_WORKSPACE_ID)})

        assert result == {"success": False, "error": "missing node_id"}
        session.execute.assert_not_called()

    async def test_returns_error_when_workspace_id_missing(self) -> None:
        session = _make_session()
        handler = _make_handler(session)

        result = await handler.handle_graph_node({"node_id": str(_NODE_ID)})

        assert result == {"success": False, "error": "missing workspace_id"}
        session.execute.assert_not_called()

    async def test_returns_error_when_node_not_found_in_db(self) -> None:
        session = _make_session()
        # execute returns a result with no rows
        mock_result = MagicMock()
        mock_result.first.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        handler = _make_handler(session)

        result = await handler.handle_graph_node(
            {"node_id": str(_NODE_ID), "workspace_id": str(_WORKSPACE_ID)}
        )

        assert result["success"] is False
        assert f"graph node {_NODE_ID} not found" in result["error"]
        session.commit.assert_not_called()


class TestHandleGraphNodeHappyPath:
    """Happy path: node found, embedding generated, stored successfully."""

    async def test_happy_path_stores_embedding_and_returns_success(self) -> None:
        session = _make_session()

        # DB returns a row with content
        mock_result = MagicMock()
        mock_result.first.return_value = ("This is the node content about Python.",)
        # Second execute call is the UPDATE — return a no-op result
        mock_update_result = MagicMock()
        session.execute = AsyncMock(side_effect=[mock_result, mock_update_result])

        handler = _make_handler(session)

        fake_embedding = [0.1] * 1536

        with patch(
            "pilot_space.infrastructure.queue.handlers.memory_embedding_handler._embed_text_openai",
            new=AsyncMock(return_value=fake_embedding),
        ):
            result = await handler.handle_graph_node(
                {"node_id": str(_NODE_ID), "workspace_id": str(_WORKSPACE_ID)}
            )

        assert result["success"] is True
        assert result["node_id"] == str(_NODE_ID)
        assert result["dims"] == 1536
        session.commit.assert_awaited_once()
        # execute called twice: SELECT then UPDATE
        assert session.execute.await_count == 2

    async def test_returns_error_when_openai_embedding_fails(self) -> None:
        session = _make_session()

        mock_result = MagicMock()
        mock_result.first.return_value = ("Node content text.",)
        session.execute = AsyncMock(return_value=mock_result)

        handler = _make_handler(session)

        with (
            patch(
                "pilot_space.infrastructure.queue.handlers.memory_embedding_handler._embed_text_openai",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "pilot_space.infrastructure.queue.handlers.memory_embedding_handler._embed_text_ollama",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await handler.handle_graph_node(
                {"node_id": str(_NODE_ID), "workspace_id": str(_WORKSPACE_ID)}
            )

        assert result["success"] is False
        assert "all embedding providers failed" in result["error"]
        session.commit.assert_not_called()


class TestHandleGraphNodeOllamaProvider:
    """Tests for the Ollama fallback/primary embedding path."""

    def _make_db(self, content: str) -> AsyncMock:
        """Build a session mock that returns content on SELECT, no-op on UPDATE."""
        select_result = MagicMock()
        select_result.first.return_value = (content,)
        update_result = MagicMock()
        session = _make_session()
        session.execute = AsyncMock(side_effect=[select_result, update_result])
        return session

    async def test_ollama_used_when_no_openai_key(self) -> None:
        """No OpenAI key → Ollama provides the embedding; result is success."""
        session = self._make_db("A decision was made to use pgvector for search.")
        handler = _make_handler(session, openai_api_key=None)
        fake_embedding = [0.42] * 768

        with patch(
            "pilot_space.infrastructure.queue.handlers.memory_embedding_handler._embed_text_ollama",
            new=AsyncMock(return_value=fake_embedding),
        ):
            result = await handler.handle_graph_node(
                {"node_id": str(_NODE_ID), "workspace_id": str(_WORKSPACE_ID)}
            )

        assert result["success"] is True
        assert result["provider"] == "ollama"
        assert result["dims"] == 768
        session.commit.assert_awaited_once()

    async def test_ollama_fallback_when_openai_fails(self) -> None:
        """OpenAI returns None → Ollama is tried and succeeds."""
        session = self._make_db("Rate limiting implemented via token bucket.")
        handler = _make_handler(session, openai_api_key="sk-test")  # pragma: allowlist secret
        fake_embedding = [0.1] * 768

        with (
            patch(
                "pilot_space.infrastructure.queue.handlers.memory_embedding_handler._embed_text_openai",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "pilot_space.infrastructure.queue.handlers.memory_embedding_handler._embed_text_ollama",
                new=AsyncMock(return_value=fake_embedding),
            ),
        ):
            result = await handler.handle_graph_node(
                {"node_id": str(_NODE_ID), "workspace_id": str(_WORKSPACE_ID)}
            )

        assert result["success"] is True
        assert result["provider"] == "ollama"
        assert result["dims"] == 768

    async def test_ollama_embedding_is_768_dim(self) -> None:
        """Ollama-produced embedding is exactly 768 dimensions."""
        session = self._make_db("Learned pattern: always add RLS policies.")
        handler = _make_handler(session, openai_api_key=None)
        fake_embedding = list(range(768))  # 0..767 — distinct values

        with patch(
            "pilot_space.infrastructure.queue.handlers.memory_embedding_handler._embed_text_ollama",
            new=AsyncMock(return_value=fake_embedding),
        ):
            result = await handler.handle_graph_node(
                {"node_id": str(_NODE_ID), "workspace_id": str(_WORKSPACE_ID)}
            )

        assert result["dims"] == 768
        # Verify the UPDATE was executed (embedding stored)
        assert session.execute.await_count == 2

    async def test_ollama_called_with_node_content(self) -> None:
        """_embed_text_ollama receives the text fetched from graph_nodes."""
        content = "Work intent: refactor knowledge graph repository."
        session = self._make_db(content)
        handler = _make_handler(session, openai_api_key=None)

        captured: list[str] = []

        async def _capture_embed(text: str, base_url: str = "") -> list[float]:
            captured.append(text)
            return [0.0] * 768

        with patch(
            "pilot_space.infrastructure.queue.handlers.memory_embedding_handler._embed_text_ollama",
            new=_capture_embed,
        ):
            result = await handler.handle_graph_node(
                {"node_id": str(_NODE_ID), "workspace_id": str(_WORKSPACE_ID)}
            )

        assert result["success"] is True
        assert captured == [content]

    async def test_ollama_sync_embed_parses_response_correctly(self) -> None:
        """_ollama_embed_sync extracts embeddings[0] from the JSON response."""
        from unittest.mock import (
            MagicMock,
            patch as stdlib_patch,
        )

        fake_vector = [round(i * 0.001, 4) for i in range(768)]
        fake_body = {"embeddings": [fake_vector]}

        mock_resp = MagicMock()
        mock_resp.read.return_value = __import__("json").dumps(fake_body).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        from pilot_space.infrastructure.queue.handlers.memory_embedding_handler import (
            _ollama_embed_sync,
        )

        with stdlib_patch("urllib.request.urlopen", return_value=mock_resp):
            result = _ollama_embed_sync("some text", "http://localhost:11434")

        assert result is not None
        assert len(result) == 768
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(0.001)
