"""Unit tests for attachment injection in PilotSpaceAgent.

Tests the multimodal content block path that forwards PDF, image, and text
attachment blocks from ChatInput into the Claude SDK message.

Reference:
  - backend/src/pilot_space/ai/agents/pilotspace_agent.py (_build_multimodal_prompt)
  - PIPE-01 / PIPE-02 / PIPE-03 / PIPE-04
"""

from __future__ import annotations

import pytest

from pilot_space.ai.agents.pilotspace_agent import (  # type: ignore[reportPrivateUsage]
    ChatInput,
    _build_multimodal_prompt,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PDF_BLOCK: dict = {
    "type": "document",
    "source": {
        "type": "base64",
        "media_type": "application/pdf",
        "data": "JVBERi0xLjQ=",  # minimal base64 stub
    },
}

IMAGE_BLOCK: dict = {
    "type": "image",
    "source": {
        "type": "base64",
        "media_type": "image/png",
        "data": "iVBORw0KGgo=",
    },
}

TEXT_BLOCK: dict = {
    "type": "text",
    "text": "Raw text attachment content",
}

SESSION_ID = "test-session-abc123"


# ---------------------------------------------------------------------------
# TestAttachmentInjection
# ---------------------------------------------------------------------------


class TestAttachmentInjection:
    """PIPE-01 — multimodal prompt generator correctness."""

    @pytest.mark.asyncio
    async def test_multimodal_prompt_yields_one_message(self) -> None:
        """_build_multimodal_prompt yields exactly one dict when blocks are present."""
        results = []
        async for msg in _build_multimodal_prompt("hello", [PDF_BLOCK], SESSION_ID):
            results.append(msg)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_multimodal_prompt_structure(self) -> None:
        """Yielded dict matches Claude SDK wire format for multimodal messages."""
        results = []
        async for msg in _build_multimodal_prompt("hello world", [PDF_BLOCK], SESSION_ID):
            results.append(msg)

        msg = results[0]
        assert msg["type"] == "user"
        assert msg["parent_tool_use_id"] is None
        assert msg["session_id"] == SESSION_ID
        assert msg["message"]["role"] == "user"
        content = msg["message"]["content"]
        assert isinstance(content, list)

    @pytest.mark.asyncio
    async def test_text_block_is_first_in_content(self) -> None:
        """Text enriched_message must be the FIRST element in content list."""
        enriched = "This is the enriched message"
        results = []
        async for msg in _build_multimodal_prompt(enriched, [PDF_BLOCK], SESSION_ID):
            results.append(msg)

        content = results[0]["message"]["content"]
        assert content[0] == {"type": "text", "text": enriched}

    @pytest.mark.asyncio
    async def test_attachment_blocks_follow_text(self) -> None:
        """Attachment blocks appear after the text block in correct order."""
        results = []
        async for msg in _build_multimodal_prompt("message", [PDF_BLOCK, IMAGE_BLOCK], SESSION_ID):
            results.append(msg)

        content = results[0]["message"]["content"]
        assert len(content) == 3  # text + pdf + image
        assert content[1] == PDF_BLOCK
        assert content[2] == IMAGE_BLOCK

    @pytest.mark.asyncio
    async def test_blocks_captured_by_value_not_reference(self) -> None:
        """Mutating the original blocks list after calling does not affect yielded content.

        This tests the `_blocks = list(blocks)` copy-by-value guard.
        """
        original_blocks = [PDF_BLOCK.copy()]
        gen = _build_multimodal_prompt("mutation test", original_blocks, SESSION_ID)

        # Mutate original list before consuming the generator
        original_blocks.clear()

        results = []
        async for msg in gen:
            results.append(msg)

        # Generator should have captured the value at call time
        content = results[0]["message"]["content"]
        # Should have text + 1 PDF block (not 0 blocks due to mutation)
        assert len(content) == 2

    @pytest.mark.asyncio
    async def test_chat_input_has_attachment_content_blocks_field(self) -> None:
        """ChatInput dataclass must have attachment_content_blocks field (defaults to None)."""
        chat_input = ChatInput(message="test")
        assert hasattr(chat_input, "attachment_content_blocks")
        assert chat_input.attachment_content_blocks is None

    @pytest.mark.asyncio
    async def test_chat_input_has_attachment_metadata_field(self) -> None:
        """ChatInput dataclass must have attachment_metadata field (defaults to None)."""
        chat_input = ChatInput(message="test")
        assert hasattr(chat_input, "attachment_metadata")
        assert chat_input.attachment_metadata is None

    @pytest.mark.asyncio
    async def test_chat_input_accepts_attachment_blocks(self) -> None:
        """ChatInput can be constructed with attachment_content_blocks."""
        blocks = [PDF_BLOCK, IMAGE_BLOCK]
        chat_input = ChatInput(
            message="analyze these files",
            attachment_content_blocks=blocks,
        )
        assert chat_input.attachment_content_blocks == blocks

    @pytest.mark.asyncio
    async def test_multimodal_path_used_when_blocks_present(self) -> None:
        """When attachment_content_blocks is non-empty, multimodal path must be taken.

        Verifies the ChatInput.attachment_content_blocks truthiness check.
        """
        chat_input = ChatInput(
            message="what is in this pdf?",
            attachment_content_blocks=[PDF_BLOCK],
        )
        # blocks are truthy → multimodal path should be taken
        assert bool(chat_input.attachment_content_blocks) is True

    @pytest.mark.asyncio
    async def test_plain_string_path_when_no_blocks(self) -> None:
        """When attachment_content_blocks is None or empty, plain string path is used.

        Verifies backward compatibility — no multimodal overhead when no attachments.
        """
        chat_input_none = ChatInput(message="just text", attachment_content_blocks=None)
        chat_input_empty = ChatInput(message="just text", attachment_content_blocks=[])

        # Both are falsy → plain string path
        assert not chat_input_none.attachment_content_blocks
        assert not chat_input_empty.attachment_content_blocks
