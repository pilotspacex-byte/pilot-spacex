"""Unit tests for Gpt4oVisionAdapter."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.ai.ocr.abstract_ocr_provider import OcrConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


def _make_config(model: str = "gpt-4o") -> OcrConfig:
    return OcrConfig(
        provider_type="gpt4o_vision",
        api_key="test-openai-key",  # pragma: allowlist secret
        model_name=model,
    )


def _make_openai_response(text: str = "Extracted text\nCONFIDENCE:0.91") -> MagicMock:
    """Build fake OpenAI chat.completions.create response."""
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=text))]
    return resp


def _make_mock_client(response_text: str = "Extracted text\nCONFIDENCE:0.91") -> MagicMock:
    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(response_text)
    )
    return mock_client


# ---------------------------------------------------------------------------
# Test 12: extract() calls chat.completions.create with image_url content block
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_calls_completions_create_with_image_url_block() -> None:
    from pilot_space.ai.ocr.gpt4o_vision_adapter import Gpt4oVisionAdapter

    config = _make_config()
    mock_client = _make_mock_client()
    adapter = Gpt4oVisionAdapter(config, openai_client=mock_client)

    await adapter.extract(_SAMPLE_PNG, "image/png")

    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs

    messages = call_kwargs["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    content_blocks = user_msg["content"]

    image_blocks = [b for b in content_blocks if b.get("type") == "image_url"]
    assert len(image_blocks) == 1


# ---------------------------------------------------------------------------
# Test 13: image_url.url = f"data:{mime_type};base64,{b64}"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_image_url_has_correct_data_uri() -> None:
    from pilot_space.ai.ocr.gpt4o_vision_adapter import Gpt4oVisionAdapter

    config = _make_config()
    mock_client = _make_mock_client()
    adapter = Gpt4oVisionAdapter(config, openai_client=mock_client)

    await adapter.extract(_SAMPLE_PNG, "image/jpeg")

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    content_blocks = user_msg["content"]

    image_block = next(b for b in content_blocks if b.get("type") == "image_url")
    expected_b64 = base64.b64encode(_SAMPLE_PNG).decode()
    expected_url = f"data:image/jpeg;base64,{expected_b64}"
    assert image_block["image_url"]["url"] == expected_url


# ---------------------------------------------------------------------------
# Test 14: model = "gpt-4o" by default (from OcrConfig.model_name default)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_uses_gpt4o_model() -> None:
    from pilot_space.ai.ocr.gpt4o_vision_adapter import Gpt4oVisionAdapter

    config = _make_config(model="gpt-4o")
    mock_client = _make_mock_client()
    adapter = Gpt4oVisionAdapter(config, openai_client=mock_client)

    await adapter.extract(_SAMPLE_PNG, "image/png")

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o"


# ---------------------------------------------------------------------------
# Test 15: OcrResult.provider_used = "gpt4o_vision"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_provider_used_is_gpt4o_vision() -> None:
    from pilot_space.ai.ocr.gpt4o_vision_adapter import Gpt4oVisionAdapter

    config = _make_config()
    mock_client = _make_mock_client()
    adapter = Gpt4oVisionAdapter(config, openai_client=mock_client)

    result = await adapter.extract(_SAMPLE_PNG, "image/png")

    assert result.provider_used == "gpt4o_vision"
