"""Unit tests for HunyuanOcrAdapter (vLLM HTTP endpoint)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pilot_space.ai.ocr.abstract_ocr_provider import OcrConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(api_key: str | None = "test-key") -> OcrConfig:
    return OcrConfig(
        provider_type="hunyuan_ocr",
        endpoint_url="http://hunyuan.local:8080",
        api_key=api_key,
        model_name="tencent/HunyuanOCR",
    )


def _make_response(content: str = "Extracted text here\nCONFIDENCE:0.95") -> MagicMock:
    """Build a fake httpx.Response-like mock."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    mock_resp.raise_for_status = MagicMock()  # no-op
    return mock_resp


_SAMPLE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20  # minimal fake PNG bytes


# ---------------------------------------------------------------------------
# Test 1: POST sent to correct URL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_posts_to_chat_completions_url() -> None:
    from pilot_space.ai.ocr.hunyuan_adapter import HunyuanOcrAdapter

    config = _make_config()
    adapter = HunyuanOcrAdapter(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_make_response())
        mock_client_cls.return_value = mock_client

        await adapter.extract(_SAMPLE_PNG, "image/png")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        url = call_args[0][0] if call_args[0] else call_args.kwargs.get("url") or call_args[0][0]
        assert url == "http://hunyuan.local:8080/v1/chat/completions"


# ---------------------------------------------------------------------------
# Test 2: Content array contains image_url block with correct data URI
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_sends_image_url_content_block() -> None:
    import base64

    from pilot_space.ai.ocr.hunyuan_adapter import HunyuanOcrAdapter

    config = _make_config()
    adapter = HunyuanOcrAdapter(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_make_response())
        mock_client_cls.return_value = mock_client

        await adapter.extract(_SAMPLE_PNG, "image/png")

        call_kwargs = mock_client.post.call_args.kwargs
        payload = call_kwargs["json"]
        user_msg = next(m for m in payload["messages"] if m["role"] == "user")
        content_blocks = user_msg["content"]

        image_blocks = [b for b in content_blocks if b.get("type") == "image_url"]
        assert len(image_blocks) == 1

        expected_b64 = base64.b64encode(_SAMPLE_PNG).decode()
        expected_url = f"data:image/png;base64,{expected_b64}"
        assert image_blocks[0]["image_url"]["url"] == expected_url


# ---------------------------------------------------------------------------
# Test 3: System message contains layout-preserving instruction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_system_message_contains_layout_instruction() -> None:
    from pilot_space.ai.ocr.hunyuan_adapter import HunyuanOcrAdapter

    config = _make_config()
    adapter = HunyuanOcrAdapter(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_make_response())
        mock_client_cls.return_value = mock_client

        await adapter.extract(_SAMPLE_PNG, "image/png")

        call_kwargs = mock_client.post.call_args.kwargs
        payload = call_kwargs["json"]
        system_msg = next(m for m in payload["messages"] if m["role"] == "system")
        assert "Extract all text" in system_msg["content"]
        assert "preserving" in system_msg["content"].lower()


# ---------------------------------------------------------------------------
# Test 4: Authorization header set when api_key present; absent when None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_authorization_header_when_api_key_present() -> None:
    from pilot_space.ai.ocr.hunyuan_adapter import HunyuanOcrAdapter

    config = _make_config(api_key="secret-key")
    adapter = HunyuanOcrAdapter(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_make_response())
        mock_client_cls.return_value = mock_client

        await adapter.extract(_SAMPLE_PNG, "image/png")

        call_kwargs = mock_client.post.call_args.kwargs
        headers = call_kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer secret-key"


@pytest.mark.asyncio
async def test_extract_no_authorization_header_when_api_key_none() -> None:
    from pilot_space.ai.ocr.hunyuan_adapter import HunyuanOcrAdapter

    config = _make_config(api_key=None)
    adapter = HunyuanOcrAdapter(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_make_response())
        mock_client_cls.return_value = mock_client

        await adapter.extract(_SAMPLE_PNG, "image/png")

        call_kwargs = mock_client.post.call_args.kwargs
        headers = call_kwargs.get("headers", {})
        assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# Test 5: CONFIDENCE line parsed as float
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_confidence_parsed_from_response() -> None:
    from pilot_space.ai.ocr.hunyuan_adapter import HunyuanOcrAdapter

    config = _make_config()
    adapter = HunyuanOcrAdapter(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_make_response("Hello world\nCONFIDENCE:0.87"))
        mock_client_cls.return_value = mock_client

        result = await adapter.extract(_SAMPLE_PNG, "image/png")

        assert result.confidence == pytest.approx(0.87)


# ---------------------------------------------------------------------------
# Test 6: CONFIDENCE line stripped from OcrResult.text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_confidence_line_stripped_from_text() -> None:
    from pilot_space.ai.ocr.hunyuan_adapter import HunyuanOcrAdapter

    config = _make_config()
    adapter = HunyuanOcrAdapter(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_make_response("Hello world\nCONFIDENCE:0.87"))
        mock_client_cls.return_value = mock_client

        result = await adapter.extract(_SAMPLE_PNG, "image/png")

        assert "CONFIDENCE" not in result.text
        assert "Hello world" in result.text


# ---------------------------------------------------------------------------
# Test 7: Timeout is 30.0 seconds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_timeout_is_30_seconds() -> None:
    from pilot_space.ai.ocr.hunyuan_adapter import HunyuanOcrAdapter

    config = _make_config()
    adapter = HunyuanOcrAdapter(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_make_response())
        mock_client_cls.return_value = mock_client

        await adapter.extract(_SAMPLE_PNG, "image/png")

        init_call = mock_client_cls.call_args
        timeout_arg = init_call.kwargs.get("timeout") or (
            init_call.args[0] if init_call.args else None
        )
        assert timeout_arg == 30.0


# ---------------------------------------------------------------------------
# Test 8: validate_connection() returns (True, None) on 200
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_connection_returns_true_on_success() -> None:
    from pilot_space.ai.ocr.hunyuan_adapter import HunyuanOcrAdapter

    config = _make_config()
    adapter = HunyuanOcrAdapter(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_make_response("Test\nCONFIDENCE:0.99"))
        mock_client_cls.return_value = mock_client

        ok, err = await adapter.validate_connection()

        assert ok is True
        assert err is None


# ---------------------------------------------------------------------------
# Test 9: validate_connection() returns (False, error_message) on TimeoutException
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_connection_returns_false_on_timeout() -> None:
    from pilot_space.ai.ocr.hunyuan_adapter import HunyuanOcrAdapter

    config = _make_config()
    adapter = HunyuanOcrAdapter(config)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Connection timed out"))
        mock_client_cls.return_value = mock_client

        ok, err = await adapter.validate_connection()

        assert ok is False
        assert err is not None
        assert len(err) > 0
