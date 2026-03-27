"""Unit tests for contextual_enrichment.enrich_chunks_with_context."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from pilot_space.ai.proxy.llm_gateway import LLMGateway, LLMResponse
from pilot_space.application.services.note.contextual_enrichment import (
    enrich_chunks_with_context,
)
from pilot_space.application.services.note.markdown_chunker import (
    MarkdownChunk,
)

# Stable workspace/user IDs for tests
_TEST_WORKSPACE_ID = UUID("11111111-1111-1111-1111-111111111111")
_TEST_USER_ID = UUID("22222222-2222-2222-2222-222222222222")


def _make_chunk(content: str, index: int = 0) -> MarkdownChunk:
    return MarkdownChunk(
        heading="Test Heading",
        heading_level=1,
        content=content,
        chunk_index=index,
        heading_hierarchy=["Test Heading"],
        token_count=len(content) // 4,
    )


def _make_mock_gateway(text: str) -> MagicMock:
    """Build a mock LLMGateway whose complete() returns an LLMResponse."""
    gateway = MagicMock(spec=LLMGateway)
    gateway.complete = AsyncMock(
        return_value=LLMResponse(
            text=text,
            input_tokens=10,
            output_tokens=5,
            model="mock-model",
            raw=None,
        )
    )
    return gateway


def _make_llm_response(text: str) -> LLMResponse:
    """Build an LLMResponse with the given text."""
    return LLMResponse(
        text=text,
        input_tokens=10,
        output_tokens=5,
        model="mock-model",
        raw=None,
    )


class TestEnrichChunksWithContext:
    """Test enrich_chunks_with_context function."""

    @pytest.mark.asyncio
    async def test_returns_unchanged_when_gateway_is_none(self) -> None:
        chunks = [_make_chunk("Some content here.", 0)]
        full_doc = "# Doc\n\nSome content here."
        result = await enrich_chunks_with_context(chunks, full_doc, llm_gateway=None)
        assert result == chunks
        assert result[0].content == "Some content here."

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_empty_input(self) -> None:
        gateway = _make_mock_gateway("unused")
        result = await enrich_chunks_with_context(
            [], "full doc", llm_gateway=gateway, workspace_id=_TEST_WORKSPACE_ID
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_adds_context_prefix_when_llm_succeeds(self) -> None:
        chunk = _make_chunk("This chunk discusses authentication.", 0)
        full_doc = "# Auth Guide\n\nThis chunk discusses authentication."
        gateway = _make_mock_gateway(
            "This section covers authentication mechanisms in the API guide."
        )

        result = await enrich_chunks_with_context(
            [chunk],
            full_doc,
            llm_gateway=gateway,
            workspace_id=_TEST_WORKSPACE_ID,
            user_id=_TEST_USER_ID,
        )

        assert len(result) == 1
        assert result[0].content.startswith("[Context:")
        assert "This chunk discusses authentication." in result[0].content

    @pytest.mark.asyncio
    async def test_returns_original_chunks_on_llm_failure(self) -> None:
        chunk = _make_chunk("Chunk content that stays unchanged.", 0)
        full_doc = "# Doc\n\nChunk content."
        gateway = MagicMock(spec=LLMGateway)
        gateway.complete = AsyncMock(side_effect=Exception("API error"))

        result = await enrich_chunks_with_context(
            [chunk],
            full_doc,
            llm_gateway=gateway,
            workspace_id=_TEST_WORKSPACE_ID,
            user_id=_TEST_USER_ID,
        )

        assert len(result) == 1
        assert result[0].content == "Chunk content that stays unchanged."

    @pytest.mark.asyncio
    async def test_content_cap_respected_with_context_prefix(self) -> None:
        # Content that fills exactly the cap
        content_cap = 200
        # Context prefix that would overflow
        long_context = "A" * 180
        chunk_content = "B" * 50  # 50 chars of actual content
        chunk = _make_chunk(chunk_content, 0)
        full_doc = "# Doc\n\n" + chunk_content
        gateway = _make_mock_gateway(long_context)

        result = await enrich_chunks_with_context(
            [chunk],
            full_doc,
            llm_gateway=gateway,
            workspace_id=_TEST_WORKSPACE_ID,
            user_id=_TEST_USER_ID,
            content_cap=content_cap,
        )

        assert len(result) == 1
        assert len(result[0].content) <= content_cap

    @pytest.mark.asyncio
    async def test_single_chunk_uses_full_document_as_context(self) -> None:
        full_doc = "# My Document\n\nSome important context."
        chunk = _make_chunk("This is chunk content.", 0)

        captured_kwargs: list[dict[str, Any]] = []

        async def capture_complete(**kwargs: Any) -> LLMResponse:
            captured_kwargs.append(kwargs)
            return _make_llm_response("Context about the document section.")

        gateway = MagicMock(spec=LLMGateway)
        gateway.complete = capture_complete

        await enrich_chunks_with_context(
            [chunk],
            full_doc,
            llm_gateway=gateway,
            workspace_id=_TEST_WORKSPACE_ID,
            user_id=_TEST_USER_ID,
        )

        assert captured_kwargs, "LLM was never called"
        messages = captured_kwargs[0].get("messages", [])
        assert "My Document" in str(messages)

    @pytest.mark.asyncio
    async def test_multiple_chunks_processed_in_parallel(self) -> None:
        chunks = [_make_chunk(f"Chunk {i} content.", i) for i in range(3)]
        full_doc = "# Doc\n\nMultiple chunks."
        call_count = 0

        async def count_calls(**kwargs: Any) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            return _make_llm_response(f"Context for call {call_count}.")

        gateway = MagicMock(spec=LLMGateway)
        gateway.complete = count_calls

        result = await enrich_chunks_with_context(
            chunks,
            full_doc,
            llm_gateway=gateway,
            workspace_id=_TEST_WORKSPACE_ID,
            user_id=_TEST_USER_ID,
        )

        assert len(result) == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_enriched_chunks_have_updated_token_count(self) -> None:
        chunk = _make_chunk("Short content.", 0)
        original_token_count = chunk.token_count
        full_doc = "# Doc\n\nShort content."
        long_context = "This is a relatively long context description."
        gateway = _make_mock_gateway(long_context)

        result = await enrich_chunks_with_context(
            [chunk],
            full_doc,
            llm_gateway=gateway,
            workspace_id=_TEST_WORKSPACE_ID,
            user_id=_TEST_USER_ID,
        )

        # Enriched content is longer → token count should increase or at least be non-zero
        assert result[0].token_count >= original_token_count

    @pytest.mark.asyncio
    async def test_partial_failure_returns_original_for_failed_chunks(self) -> None:
        """If one chunk's LLM call fails, that chunk is unchanged; others are enriched."""
        chunks = [_make_chunk(f"Chunk {i}.", i) for i in range(3)]
        full_doc = "# Doc\n\nMultiple chunks."
        call_count = 0

        async def flaky_complete(**kwargs: Any) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Transient failure")
            return _make_llm_response("Good context.")

        gateway = MagicMock(spec=LLMGateway)
        gateway.complete = flaky_complete

        result = await enrich_chunks_with_context(
            chunks,
            full_doc,
            llm_gateway=gateway,
            workspace_id=_TEST_WORKSPACE_ID,
            user_id=_TEST_USER_ID,
        )

        assert len(result) == 3
        # The failed chunk (index 1) stays as original
        assert result[1].content == "Chunk 1."
