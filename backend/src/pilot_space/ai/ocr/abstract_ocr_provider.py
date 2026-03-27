"""Abstract OCR provider contract and result dataclasses."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class MarkdownTable:
    """A table extracted from an image, serialised as GFM markdown."""

    markdown: str
    row_count: int
    col_count: int


@dataclass
class LayoutBlock:
    """A positioned block of text from the document layout analysis."""

    text: str
    block_type: str  # "heading" | "paragraph" | "list" | "table" | "other"
    confidence: float


@dataclass
class OcrResult:
    """Provider-agnostic OCR extraction result."""

    text: str
    tables: list[MarkdownTable] = field(default_factory=list)
    confidence: float = 0.0
    language: str = "unknown"
    layout_blocks: list[LayoutBlock] = field(default_factory=list)
    provider_used: str = ""


@dataclass
class OcrConfig:
    """Unified config passed to all OCR adapter constructors."""

    provider_type: str
    # HunyuanOCR fields (vLLM HTTP endpoint)
    endpoint_url: str | None = None
    api_key: str | None = None
    model_name: str = "tencent/HunyuanOCR"
    # TencentCloud fields — stored as JSON blob in encrypted_key: {"id":"...","key":"..."}
    secret_id: str | None = None
    secret_key: str | None = None
    region: str = "ap-guangzhou"


def parse_confidence(text: str) -> tuple[float, str]:
    """Extract CONFIDENCE:0.95 line from OCR response.

    Returns:
        Tuple of (confidence_float, cleaned_text_without_confidence_line).
        If no CONFIDENCE line found, returns (0.0, original_text).
    """
    match = re.search(r"CONFIDENCE:(\d+\.\d+)\s*$", text.strip())
    if match:
        confidence = float(match.group(1))
        clean = text[: match.start()].rstrip()
        return confidence, clean
    return 0.0, text


class AbstractOcrProvider(ABC):
    """Abstract base class for all OCR provider adapters.

    Implementors must provide:
    - extract(): process image bytes and return OcrResult
    - validate_connection(): test that the provider endpoint is reachable
    """

    @abstractmethod
    async def extract(
        self,
        image_data: bytes,
        mime_type: str,
        prompt: str | None = None,
    ) -> OcrResult:
        """Extract text and structure from image bytes.

        Args:
            image_data: Raw image bytes (PNG, JPEG, WEBP, etc.).
            mime_type: MIME type of the image (e.g. "image/png").
            prompt: Optional guidance prompt for vision-capable models.

        Returns:
            OcrResult with extracted text, tables, layout blocks.
        """

    @abstractmethod
    async def validate_connection(self) -> tuple[bool, str | None]:
        """Verify the provider endpoint is reachable and credentials are valid.

        Returns:
            Tuple of (is_valid, error_message). error_message is None on success.
        """


__all__ = [
    "AbstractOcrProvider",
    "LayoutBlock",
    "MarkdownTable",
    "OcrConfig",
    "OcrResult",
    "parse_confidence",
]
