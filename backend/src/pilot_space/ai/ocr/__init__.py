"""Provider-agnostic OCR service layer."""

from .abstract_ocr_provider import (
    AbstractOcrProvider,
    LayoutBlock,
    MarkdownTable,
    OcrConfig,
    OcrResult,
)
from .factory import OcrProviderFactory

__all__ = [
    "AbstractOcrProvider",
    "LayoutBlock",
    "MarkdownTable",
    "OcrConfig",
    "OcrProviderFactory",
    "OcrResult",
]
