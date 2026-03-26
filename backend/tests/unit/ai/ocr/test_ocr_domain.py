"""Unit tests for OCR domain contracts.

Tests for:
- Task 1: SecureKeyStorage VALID_SERVICE_TYPES and VALID_PROVIDERS for OCR
- Task 2: OcrResult, MarkdownTable, LayoutBlock, OcrConfig dataclasses
- Task 2: AbstractOcrProvider ABC enforcement
- Task 2: OcrProviderFactory routing
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
from pilot_space.ai.providers.constants import VALID_PROVIDERS

# ---------------------------------------------------------------------------
# Task 1: Key storage OCR support
# ---------------------------------------------------------------------------


class TestOcrKeyStorageConstants:
    """Tests 1-2: VALID_SERVICE_TYPES and VALID_PROVIDERS contain OCR entries."""

    def test_valid_service_types_contains_ocr(self) -> None:
        """Test 1: SecureKeyStorage.VALID_SERVICE_TYPES contains 'ocr'."""
        assert "ocr" in SecureKeyStorage.VALID_SERVICE_TYPES

    def test_valid_providers_contains_hunyuan_ocr(self) -> None:
        """Test 2a: SecureKeyStorage.VALID_PROVIDERS contains 'hunyuan_ocr'."""
        assert "hunyuan_ocr" in SecureKeyStorage.VALID_PROVIDERS

    def test_valid_providers_contains_tencent_ocr(self) -> None:
        """Test 2b: SecureKeyStorage.VALID_PROVIDERS contains 'tencent_ocr'."""
        assert "tencent_ocr" in SecureKeyStorage.VALID_PROVIDERS

    def test_valid_providers_frozenset_includes_ocr_providers(self) -> None:
        """Test 6: VALID_PROVIDERS frozenset is recomputed and includes OCR providers."""
        assert "hunyuan_ocr" in VALID_PROVIDERS
        assert "tencent_ocr" in VALID_PROVIDERS
        # Ensure existing providers still present
        assert "anthropic" in VALID_PROVIDERS
        assert "google" in VALID_PROVIDERS
        assert "ollama" in VALID_PROVIDERS


@pytest.mark.asyncio
class TestOcrKeyStorageStoreApiKey:
    """Tests 3-5: store_api_key validation for OCR providers."""

    def _make_storage(self) -> SecureKeyStorage:
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        return SecureKeyStorage(db, master_secret="test-secret")  # pragma: allowlist secret

    async def test_store_api_key_hunyuan_ocr_does_not_raise(self) -> None:
        """Test 3: store_api_key with hunyuan_ocr/ocr does NOT raise ValueError."""
        storage = self._make_storage()
        workspace_id = uuid4()
        # Should not raise — validation check passes before DB access
        await storage.store_api_key(
            workspace_id=workspace_id,
            provider="hunyuan_ocr",
            service_type="ocr",
            api_key="test-key-hunyuan",  # pragma: allowlist secret
        )

    async def test_store_api_key_tencent_ocr_does_not_raise(self) -> None:
        """Test 4: store_api_key with tencent_ocr/ocr does NOT raise ValueError."""
        storage = self._make_storage()
        workspace_id = uuid4()
        await storage.store_api_key(
            workspace_id=workspace_id,
            provider="tencent_ocr",
            service_type="ocr",
            api_key="test-key-tencent",  # pragma: allowlist secret
        )

    async def test_store_api_key_hunyuan_ocr_with_llm_raises_value_error(self) -> None:
        """Test 5: store_api_key with hunyuan_ocr/llm raises ValueError (wrong service type)."""
        storage = self._make_storage()
        workspace_id = uuid4()
        # hunyuan_ocr only supports "ocr" — using "llm" must raise
        with pytest.raises(ValueError, match="does not support service_type"):
            await storage.store_api_key(
                workspace_id=workspace_id,
                provider="hunyuan_ocr",
                service_type="llm",
                api_key="test-key",  # pragma: allowlist secret
            )


# ---------------------------------------------------------------------------
# Task 2: OCR domain dataclasses and ABC
# ---------------------------------------------------------------------------


class TestOcrDataclasses:
    """Tests 7-9: OcrResult, MarkdownTable, LayoutBlock dataclasses."""

    def test_ocr_result_defaults(self) -> None:
        """Test 7: OcrResult instantiates with only text; defaults are correct."""
        from pilot_space.ai.ocr import OcrResult

        result = OcrResult(text="hello")
        assert result.text == "hello"
        assert result.tables == []
        assert result.confidence == 0.0
        assert result.language == "unknown"
        assert result.layout_blocks == []
        assert result.provider_used == ""

    def test_markdown_table_fields(self) -> None:
        """Test 8: MarkdownTable has markdown, row_count, col_count fields."""
        from pilot_space.ai.ocr import MarkdownTable

        table = MarkdownTable(markdown="| a | b |", row_count=1, col_count=2)
        assert table.markdown == "| a | b |"
        assert table.row_count == 1
        assert table.col_count == 2

    def test_layout_block_fields(self) -> None:
        """Test 9: LayoutBlock has text, block_type, confidence fields."""
        from pilot_space.ai.ocr import LayoutBlock

        block = LayoutBlock(text="Title", block_type="heading", confidence=0.95)
        assert block.text == "Title"
        assert block.block_type == "heading"
        assert block.confidence == 0.95


class TestAbstractOcrProvider:
    """Tests 10-11: AbstractOcrProvider ABC enforcement."""

    def test_abstract_ocr_provider_cannot_be_instantiated(self) -> None:
        """Test 10: AbstractOcrProvider cannot be instantiated directly."""
        from pilot_space.ai.ocr import AbstractOcrProvider

        with pytest.raises(TypeError):
            AbstractOcrProvider()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        """Test 11: Concrete subclass implementing all abstract methods can be instantiated."""
        from pilot_space.ai.ocr import AbstractOcrProvider, OcrResult

        class ConcreteProvider(AbstractOcrProvider):
            async def extract(
                self,
                image_data: bytes,
                mime_type: str,
                prompt: str | None = None,
            ) -> OcrResult:
                return OcrResult(text="extracted")

            async def validate_connection(self) -> tuple[bool, str | None]:
                return True, None

        provider = ConcreteProvider()
        assert isinstance(provider, AbstractOcrProvider)


class TestOcrProviderFactory:
    """Tests 12-16: OcrProviderFactory.create() routing."""

    def _make_config(self, provider_type: str):  # type: ignore[no-untyped-def]
        from pilot_space.ai.ocr import OcrConfig

        return OcrConfig(provider_type=provider_type)

    def test_factory_creates_hunyuan_ocr_adapter(self) -> None:
        """Test 12: create('hunyuan_ocr', config) returns HunyuanOcrAdapter."""
        from pilot_space.ai.ocr import OcrProviderFactory
        from pilot_space.ai.ocr.hunyuan_adapter import HunyuanOcrAdapter

        config = self._make_config("hunyuan_ocr")
        adapter = OcrProviderFactory.create("hunyuan_ocr", config)
        assert isinstance(adapter, HunyuanOcrAdapter)

    def test_factory_creates_tencent_ocr_adapter(self) -> None:
        """Test 13: create('tencent_ocr', config) returns TencentCloudOcrAdapter."""
        from pilot_space.ai.ocr import OcrProviderFactory
        from pilot_space.ai.ocr.tencent_adapter import TencentCloudOcrAdapter

        config = self._make_config("tencent_ocr")
        adapter = OcrProviderFactory.create("tencent_ocr", config)
        assert isinstance(adapter, TencentCloudOcrAdapter)

    def test_factory_creates_claude_vision_adapter(self) -> None:
        """Test 14: create('claude_vision', config) returns ClaudeVisionAdapter."""
        from pilot_space.ai.ocr import OcrProviderFactory
        from pilot_space.ai.ocr.claude_vision_adapter import ClaudeVisionAdapter

        config = self._make_config("claude_vision")
        adapter = OcrProviderFactory.create("claude_vision", config)
        assert isinstance(adapter, ClaudeVisionAdapter)

    def test_factory_creates_gpt4o_vision_adapter(self) -> None:
        """Test 15: create('gpt4o_vision', config) returns Gpt4oVisionAdapter."""
        from pilot_space.ai.ocr import OcrProviderFactory
        from pilot_space.ai.ocr.gpt4o_vision_adapter import Gpt4oVisionAdapter

        config = self._make_config("gpt4o_vision")
        adapter = OcrProviderFactory.create("gpt4o_vision", config)
        assert isinstance(adapter, Gpt4oVisionAdapter)

    def test_factory_raises_for_unknown_provider(self) -> None:
        """Test 16: create('unknown_provider', config) raises ValueError."""
        from pilot_space.ai.ocr import OcrProviderFactory

        config = self._make_config("unknown_provider")
        with pytest.raises(ValueError, match="Unknown OCR provider type"):
            OcrProviderFactory.create("unknown_provider", config)
