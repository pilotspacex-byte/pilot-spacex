"""Unit tests for TencentCloudOcrAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.ai.ocr.abstract_ocr_provider import OcrConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

# Patch targets — tencentcloud SDK may not be installed in CI
_P_CRED = "pilot_space.ai.ocr.tencent_adapter.Credential"
_P_CLIENT = "pilot_space.ai.ocr.tencent_adapter.OcrClient"
_P_MODELS = "pilot_space.ai.ocr.tencent_adapter.ocr_models"


def _make_config() -> OcrConfig:
    return OcrConfig(
        provider_type="tencent_ocr",
        secret_id="test-secret-id",  # pragma: allowlist secret
        secret_key="test-secret-key",  # pragma: allowlist secret
        region="ap-guangzhou",
    )


def _make_tencent_response(texts: list[str]) -> MagicMock:
    """Build fake Tencent GeneralAccurateOCR response."""
    resp = MagicMock()
    resp.TextDetections = [MagicMock(DetectedText=t) for t in texts]
    return resp


# ---------------------------------------------------------------------------
# Test 1: extract() calls GeneralAccurateOCR via run_in_executor (not directly)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_uses_run_in_executor() -> None:
    from pilot_space.ai.ocr.tencent_adapter import TencentCloudOcrAdapter

    config = _make_config()
    adapter = TencentCloudOcrAdapter(config)

    with (
        patch(_P_CRED),
        patch(_P_CLIENT) as mock_ocr_cls,
        patch(_P_MODELS),
        patch("asyncio.get_event_loop") as mock_loop,
    ):
        mock_ocr_cls.return_value = MagicMock()
        mock_loop_inst = MagicMock()
        mock_loop.return_value = mock_loop_inst
        mock_loop_inst.run_in_executor = AsyncMock(
            return_value=_make_tencent_response(["Hello world"])
        )

        await adapter.extract(_SAMPLE_PNG, "image/png")

        mock_loop_inst.run_in_executor.assert_called_once()
        args = mock_loop_inst.run_in_executor.call_args[0]
        assert args[0] is None


# ---------------------------------------------------------------------------
# Test 2: ImageBase64 is set to base64-encoded image_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_sets_image_base64() -> None:
    from pilot_space.ai.ocr.tencent_adapter import TencentCloudOcrAdapter

    config = _make_config()
    adapter = TencentCloudOcrAdapter(config)

    with (
        patch(_P_CRED),
        patch(_P_CLIENT) as mock_ocr_cls,
        patch(_P_MODELS),
        patch("asyncio.get_event_loop") as mock_loop,
    ):
        mock_ocr_cls.return_value = MagicMock()
        mock_loop_inst = MagicMock()
        mock_loop.return_value = mock_loop_inst
        mock_loop_inst.run_in_executor = AsyncMock(return_value=_make_tencent_response(["text"]))

        await adapter.extract(_SAMPLE_PNG, "image/png")

        mock_loop_inst.run_in_executor.assert_called_once()
        args = mock_loop_inst.run_in_executor.call_args[0]
        assert len(args) >= 2


# ---------------------------------------------------------------------------
# Test 3: OcrResult.text is newline-joined DetectedText values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_text_joins_detected_texts() -> None:
    from pilot_space.ai.ocr.tencent_adapter import TencentCloudOcrAdapter

    config = _make_config()
    adapter = TencentCloudOcrAdapter(config)
    texts = ["Line one", "Line two", "Line three"]

    with (
        patch(_P_CRED),
        patch(_P_CLIENT),
        patch(_P_MODELS),
        patch("asyncio.get_event_loop") as mock_loop,
    ):
        mock_loop_inst = MagicMock()
        mock_loop.return_value = mock_loop_inst
        mock_loop_inst.run_in_executor = AsyncMock(return_value=_make_tencent_response(texts))

        result = await adapter.extract(_SAMPLE_PNG, "image/png")

        assert result.text == "Line one\nLine two\nLine three"


# ---------------------------------------------------------------------------
# Test 4: OcrResult.provider_used = "tencent_ocr"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_provider_used_is_tencent_ocr() -> None:
    from pilot_space.ai.ocr.tencent_adapter import TencentCloudOcrAdapter

    config = _make_config()
    adapter = TencentCloudOcrAdapter(config)

    with (
        patch(_P_CRED),
        patch(_P_CLIENT),
        patch(_P_MODELS),
        patch("asyncio.get_event_loop") as mock_loop,
    ):
        mock_loop_inst = MagicMock()
        mock_loop.return_value = mock_loop_inst
        mock_loop_inst.run_in_executor = AsyncMock(return_value=_make_tencent_response(["text"]))

        result = await adapter.extract(_SAMPLE_PNG, "image/png")

        assert result.provider_used == "tencent_ocr"


# ---------------------------------------------------------------------------
# Test 5: validate_connection() returns (True, None) on success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_connection_returns_true_on_success() -> None:
    from pilot_space.ai.ocr.tencent_adapter import TencentCloudOcrAdapter

    config = _make_config()
    adapter = TencentCloudOcrAdapter(config)

    with (
        patch(_P_CRED),
        patch(_P_CLIENT),
        patch(_P_MODELS),
        patch("asyncio.get_event_loop") as mock_loop,
    ):
        mock_loop_inst = MagicMock()
        mock_loop.return_value = mock_loop_inst
        mock_loop_inst.run_in_executor = AsyncMock(return_value=_make_tencent_response(["ok"]))

        ok, err = await adapter.validate_connection()

        assert ok is True
        assert err is None


# ---------------------------------------------------------------------------
# Test 6: validate_connection() returns (False, str(exc)) on SDK exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_connection_returns_false_on_sdk_exception() -> None:
    from pilot_space.ai.ocr.tencent_adapter import TencentCloudOcrAdapter

    config = _make_config()
    adapter = TencentCloudOcrAdapter(config)

    with (
        patch(_P_CRED),
        patch(_P_CLIENT),
        patch(_P_MODELS),
        patch("asyncio.get_event_loop") as mock_loop,
    ):
        mock_loop_inst = MagicMock()
        mock_loop.return_value = mock_loop_inst
        mock_loop_inst.run_in_executor = AsyncMock(side_effect=RuntimeError("SDK auth failure"))

        ok, err = await adapter.validate_connection()

        assert ok is False
        assert err is not None
        assert "SDK auth failure" in err
