"""Unit tests for OcrService — cascade fallback orchestrator.

Tests cover:
- Cascade fallback through provider chain (primary → Claude → GPT-4o)
- All-providers-fail path returns empty OcrResult
- DB persistence after successful extraction
- _build_fallback_chain with various key configurations
- is_scanned_pdf() helper
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.ocr.abstract_ocr_provider import OcrResult
from pilot_space.application.services.ai.ocr_service import OcrService, is_scanned_pdf

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WORKSPACE_ID = uuid4()
ATTACHMENT_ID = uuid4()
IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal fake PNG


def _mock_session() -> MagicMock:
    """Create a mock AsyncSession."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


def _mock_provider(text: str = "extracted text", provider_used: str = "hunyuan_ocr") -> MagicMock:
    """Create a mock OCR provider that returns a successful OcrResult."""
    provider = MagicMock()
    provider.extract = AsyncMock(return_value=OcrResult(text=text, provider_used=provider_used))
    return provider


def _failing_provider(exc: Exception | None = None) -> MagicMock:
    """Create a mock OCR provider whose extract() raises an exception."""
    provider = MagicMock()
    provider.extract = AsyncMock(side_effect=exc or Exception("provider failed"))
    return provider


# ---------------------------------------------------------------------------
# Task 1 Tests — extract_with_fallback cascade
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_with_fallback_primary_success() -> None:
    """Test 1: extract_with_fallback() with hunyuan_ocr configured — tries primary first; on success returns its OcrResult."""
    service = OcrService(master_secret="test-secret")
    session = _mock_session()
    primary = _mock_provider(text="hello world", provider_used="hunyuan_ocr")

    with (
        patch.object(service, "_build_fallback_chain", AsyncMock(return_value=[primary])),
        patch.object(service, "_persist_result", AsyncMock()),
    ):
        result = await service.extract_with_fallback(
            IMAGE_BYTES, "image/png", WORKSPACE_ID, ATTACHMENT_ID, session
        )

    assert result.text == "hello world"
    assert result.provider_used == "hunyuan_ocr"
    primary.extract.assert_called_once_with(IMAGE_BYTES, "image/png")


@pytest.mark.asyncio
async def test_extract_with_fallback_primary_timeout_uses_claude() -> None:
    """Test 2: primary fails with timeout, falls back to ClaudeVisionAdapter."""
    import httpx

    service = OcrService(master_secret="test-secret")
    session = _mock_session()
    primary = _failing_provider(exc=httpx.TimeoutException("timed out"))
    claude = _mock_provider(text="claude extracted", provider_used="claude_vision")

    with (
        patch.object(service, "_build_fallback_chain", AsyncMock(return_value=[primary, claude])),
        patch.object(service, "_persist_result", AsyncMock()),
    ):
        result = await service.extract_with_fallback(
            IMAGE_BYTES, "image/png", WORKSPACE_ID, ATTACHMENT_ID, session
        )

    assert result.text == "claude extracted"
    assert result.provider_used == "claude_vision"
    primary.extract.assert_called_once()
    claude.extract.assert_called_once()


@pytest.mark.asyncio
async def test_extract_with_fallback_primary_and_claude_fail_uses_gpt4o() -> None:
    """Test 3: primary fails, Claude fails, falls back to Gpt4oVisionAdapter."""
    service = OcrService(master_secret="test-secret")
    session = _mock_session()
    primary = _failing_provider()
    claude = _failing_provider(exc=RuntimeError("anthropic error"))
    gpt4o = _mock_provider(text="gpt4o extracted", provider_used="gpt4o_vision")

    with (
        patch.object(
            service, "_build_fallback_chain", AsyncMock(return_value=[primary, claude, gpt4o])
        ),
        patch.object(service, "_persist_result", AsyncMock()),
    ):
        result = await service.extract_with_fallback(
            IMAGE_BYTES, "image/png", WORKSPACE_ID, ATTACHMENT_ID, session
        )

    assert result.text == "gpt4o extracted"
    assert result.provider_used == "gpt4o_vision"
    gpt4o.extract.assert_called_once()


@pytest.mark.asyncio
async def test_extract_with_fallback_all_fail_returns_empty() -> None:
    """Test 4: all providers fail, returns OcrResult(text='', provider_used='none') without raising."""
    service = OcrService(master_secret="test-secret")
    session = _mock_session()
    providers_list = [_failing_provider(), _failing_provider(), _failing_provider()]

    with patch.object(service, "_build_fallback_chain", AsyncMock(return_value=providers_list)):
        result = await service.extract_with_fallback(
            IMAGE_BYTES, "image/png", WORKSPACE_ID, ATTACHMENT_ID, session
        )

    assert result.text == ""
    assert result.provider_used == "none"


@pytest.mark.asyncio
async def test_successful_extraction_persists_to_db() -> None:
    """Test 5: successful extraction persists OcrResultModel to DB with correct fields."""
    from pilot_space.infrastructure.database.models.ocr_result import OcrResultModel

    service = OcrService(master_secret="test-secret")
    session = _mock_session()
    primary = _mock_provider(text="persisted text", provider_used="hunyuan_ocr")

    with patch.object(service, "_build_fallback_chain", AsyncMock(return_value=[primary])):
        await service.extract_with_fallback(
            IMAGE_BYTES, "image/png", WORKSPACE_ID, ATTACHMENT_ID, session
        )

    # session.add should have been called with an OcrResultModel instance
    session.add.assert_called_once()
    added_obj = session.add.call_args[0][0]
    assert isinstance(added_obj, OcrResultModel)
    assert added_obj.extracted_text == "persisted text"
    assert added_obj.provider_used == "hunyuan_ocr"
    assert added_obj.attachment_id == ATTACHMENT_ID
    session.flush.assert_called_once()


# ---------------------------------------------------------------------------
# Task 1 Tests — _build_fallback_chain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_fallback_chain_with_hunyuan_and_anthropic() -> None:
    """Test 6: chain is [hunyuan_ocr_provider, claude_vision] when workspace has both configured."""
    from datetime import UTC, datetime

    from pilot_space.ai.infrastructure.key_storage import APIKeyInfo

    service = OcrService(master_secret="test-secret")
    session = _mock_session()

    fake_info = APIKeyInfo(
        workspace_id=WORKSPACE_ID,
        provider="hunyuan_ocr",
        service_type="ocr",
        is_valid=True,
        last_validated_at=None,
        validation_error=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        base_url="http://localhost:8080/v1",
        model_name="tencent/HunyuanOCR",
    )

    with patch("pilot_space.application.services.ai.ocr_service.SecureKeyStorage") as MockStorage:
        mock_storage = MockStorage.return_value
        mock_storage.get_key_info = AsyncMock(
            side_effect=lambda _ws, provider, _svc: fake_info if provider == "hunyuan_ocr" else None
        )
        mock_storage.get_api_key = AsyncMock(
            side_effect=lambda _ws, provider, _svc: (
                "test-hunyuan-key"
                if provider == "hunyuan_ocr"
                else ("sk-ant-test" if provider == "anthropic" else None)
            )
        )

        with patch(
            "pilot_space.application.services.ai.ocr_service.OcrProviderFactory"
        ) as MockFactory:
            mock_factory_create = MagicMock()
            MockFactory.create = MagicMock(return_value=mock_factory_create)

            chain = await service._build_fallback_chain(WORKSPACE_ID, session)

    # Should have created two providers: hunyuan_ocr + claude_vision
    assert len(chain) == 2
    calls = MockFactory.create.call_args_list
    assert calls[0][0][0] == "hunyuan_ocr"
    assert calls[1][0][0] == "claude_vision"


@pytest.mark.asyncio
async def test_build_fallback_chain_no_ocr_provider_only_claude() -> None:
    """Test 7: chain is [claude_vision] when no dedicated OCR provider configured but anthropic LLM exists."""
    service = OcrService(master_secret="test-secret")
    session = _mock_session()

    with patch("pilot_space.application.services.ai.ocr_service.SecureKeyStorage") as MockStorage:
        mock_storage = MockStorage.return_value
        # No dedicated OCR provider
        mock_storage.get_key_info = AsyncMock(return_value=None)
        # Anthropic LLM key exists
        mock_storage.get_api_key = AsyncMock(return_value="sk-ant-test")

        with patch(
            "pilot_space.application.services.ai.ocr_service.OcrProviderFactory"
        ) as MockFactory:
            mock_provider = MagicMock()
            MockFactory.create = MagicMock(return_value=mock_provider)

            chain = await service._build_fallback_chain(WORKSPACE_ID, session)

    # Only claude_vision since no OCR provider
    assert len(chain) == 1
    calls = MockFactory.create.call_args_list
    assert calls[0][0][0] == "claude_vision"


@pytest.mark.asyncio
async def test_build_fallback_chain_no_providers_returns_empty() -> None:
    """Test 8: chain is [] when no providers at all configured."""
    service = OcrService(master_secret="test-secret")
    session = _mock_session()

    with patch("pilot_space.application.services.ai.ocr_service.SecureKeyStorage") as MockStorage:
        mock_storage = MockStorage.return_value
        mock_storage.get_key_info = AsyncMock(return_value=None)
        mock_storage.get_api_key = AsyncMock(return_value=None)

        chain = await service._build_fallback_chain(WORKSPACE_ID, session)

    assert chain == []


# ---------------------------------------------------------------------------
# Task 1 Tests — is_scanned_pdf()
# ---------------------------------------------------------------------------


def _make_minimal_pdf_with_text(text: str) -> bytes:
    """Build a minimal PDF with embedded text using low-level PDF syntax."""
    # Create a minimal but valid PDF with embedded text via pypdf-compatible structure
    # We'll use a simple hand-crafted PDF with text in content stream
    content_stream = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode()

    xref_positions: list[int] = []
    parts: list[bytes] = []

    header = b"%PDF-1.4\n"
    parts.append(header)
    pos = len(header)

    # Object 1: Catalog
    xref_positions.append(pos)
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    parts.append(obj1)
    pos += len(obj1)

    # Object 2: Pages
    xref_positions.append(pos)
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    parts.append(obj2)
    pos += len(obj2)

    # Object 3: Page
    xref_positions.append(pos)
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    parts.append(obj3)
    pos += len(obj3)

    # Object 4: Content stream
    xref_positions.append(pos)
    stream_len = len(content_stream)
    obj4 = (
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode()
        + content_stream
        + b"\nendstream\nendobj\n"
    )
    parts.append(obj4)
    pos += len(obj4)

    # Object 5: Font
    xref_positions.append(pos)
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    parts.append(obj5)
    pos += len(obj5)

    # xref table
    xref_start = pos
    xref_table = b"xref\n0 6\n"
    xref_table += b"0000000000 65535 f \n"
    for xp in xref_positions:
        xref_table += f"{xp:010d} 00000 n \n".encode()
    parts.append(xref_table)

    # trailer
    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode()
    parts.append(trailer)

    return b"".join(parts)


def _make_empty_pdf() -> bytes:
    """Build a minimal PDF with no text content."""
    return _make_minimal_pdf_with_text("")


@pytest.mark.asyncio
async def test_is_scanned_pdf_false_for_text_pdf() -> None:
    """Test 9: is_scanned_pdf() returns False for a PDF with > 100 chars of embedded text."""
    long_text = "This is a text-layer PDF with lots of embedded content. " * 5  # ~280 chars
    pdf_bytes = _make_minimal_pdf_with_text(long_text)
    result = await is_scanned_pdf(pdf_bytes)
    assert result is False


@pytest.mark.asyncio
async def test_is_scanned_pdf_true_for_empty_pdf() -> None:
    """Test 10: is_scanned_pdf() returns True for a PDF with 0-99 chars of embedded text."""
    pdf_bytes = _make_empty_pdf()
    result = await is_scanned_pdf(pdf_bytes)
    assert result is True
