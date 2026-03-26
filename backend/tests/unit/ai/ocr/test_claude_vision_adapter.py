"""Unit tests for ClaudeVisionAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.ai.ocr.abstract_ocr_provider import OcrConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


def _make_config() -> OcrConfig:
    return OcrConfig(
        provider_type="claude_vision",
        api_key="test-anthropic-key",  # pragma: allowlist secret
    )


def _make_anthropic_response(text: str = "Extracted text\nCONFIDENCE:0.92") -> MagicMock:
    """Build fake Anthropic messages.create response."""
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    return resp


def _make_mock_client(response_text: str = "Extracted text\nCONFIDENCE:0.92") -> MagicMock:
    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_make_anthropic_response(response_text))
    return mock_client


# ---------------------------------------------------------------------------
# Test 7: extract() calls messages.create with base64 image content block
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_calls_messages_create_with_image_block() -> None:
    from pilot_space.ai.ocr.claude_vision_adapter import ClaudeVisionAdapter

    config = _make_config()
    mock_client = _make_mock_client()
    adapter = ClaudeVisionAdapter(config, anthropic_client=mock_client)

    await adapter.extract(_SAMPLE_PNG, "image/png")

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs

    messages = call_kwargs["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    content_blocks = user_msg["content"]

    image_blocks = [b for b in content_blocks if b.get("type") == "image"]
    assert len(image_blocks) == 1
    assert image_blocks[0]["source"]["type"] == "base64"


# ---------------------------------------------------------------------------
# Test 8: Image source has media_type equal to mime_type argument
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_image_source_has_correct_media_type() -> None:
    import base64

    from pilot_space.ai.ocr.claude_vision_adapter import ClaudeVisionAdapter

    config = _make_config()
    mock_client = _make_mock_client()
    adapter = ClaudeVisionAdapter(config, anthropic_client=mock_client)

    await adapter.extract(_SAMPLE_PNG, "image/jpeg")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    messages = call_kwargs["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    content_blocks = user_msg["content"]

    image_block = next(b for b in content_blocks if b.get("type") == "image")
    assert image_block["source"]["media_type"] == "image/jpeg"

    expected_b64 = base64.b64encode(_SAMPLE_PNG).decode()
    assert image_block["source"]["data"] == expected_b64


# ---------------------------------------------------------------------------
# Test 9: System prompt instructs layout-preserving OCR with markdown tables
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_system_prompt_contains_ocr_instruction() -> None:
    from pilot_space.ai.ocr.claude_vision_adapter import ClaudeVisionAdapter

    config = _make_config()
    mock_client = _make_mock_client()
    adapter = ClaudeVisionAdapter(config, anthropic_client=mock_client)

    await adapter.extract(_SAMPLE_PNG, "image/png")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    system = call_kwargs.get("system", "")
    assert "Extract all text" in system
    assert "markdown" in system.lower() or "layout" in system.lower()


# ---------------------------------------------------------------------------
# Test 10: OcrResult.text is response.content[0].text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_result_text_from_response_content() -> None:
    from pilot_space.ai.ocr.claude_vision_adapter import ClaudeVisionAdapter

    config = _make_config()
    mock_client = _make_mock_client("Invoice total: $1,234.56\nCONFIDENCE:0.97")
    adapter = ClaudeVisionAdapter(config, anthropic_client=mock_client)

    result = await adapter.extract(_SAMPLE_PNG, "image/png")

    assert "Invoice total" in result.text
    assert "CONFIDENCE" not in result.text


# ---------------------------------------------------------------------------
# Test 11: OcrResult.provider_used = "claude_vision"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_provider_used_is_claude_vision() -> None:
    from pilot_space.ai.ocr.claude_vision_adapter import ClaudeVisionAdapter

    config = _make_config()
    mock_client = _make_mock_client()
    adapter = ClaudeVisionAdapter(config, anthropic_client=mock_client)

    result = await adapter.extract(_SAMPLE_PNG, "image/png")

    assert result.provider_used == "claude_vision"
