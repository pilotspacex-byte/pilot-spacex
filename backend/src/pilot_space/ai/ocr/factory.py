"""OCR provider factory — routes provider_type slug to the correct adapter class."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .abstract_ocr_provider import AbstractOcrProvider, OcrConfig

_PROVIDER_MAP: dict[str, str] = {
    "hunyuan_ocr": "pilot_space.ai.ocr.hunyuan_adapter.HunyuanOcrAdapter",
    "tencent_ocr": "pilot_space.ai.ocr.tencent_adapter.TencentCloudOcrAdapter",
    "claude_vision": "pilot_space.ai.ocr.claude_vision_adapter.ClaudeVisionAdapter",
    "gpt4o_vision": "pilot_space.ai.ocr.gpt4o_vision_adapter.Gpt4oVisionAdapter",
}


class OcrProviderFactory:
    """Factory that instantiates the correct OCR adapter for a given provider slug.

    Adapters are imported lazily so unused provider libraries are not loaded at
    startup (e.g. tencentcloud SDK is only imported when tencent_ocr is used).
    """

    @classmethod
    def create(cls, provider_type: str, config: OcrConfig) -> AbstractOcrProvider:
        """Instantiate the OCR adapter matching provider_type.

        Args:
            provider_type: Provider slug — one of "hunyuan_ocr", "tencent_ocr",
                           "claude_vision", "gpt4o_vision".
            config: Adapter configuration (credentials, endpoint URL, etc.).

        Returns:
            Concrete AbstractOcrProvider instance.

        Raises:
            ValueError: If provider_type is not recognised.
        """
        if provider_type not in _PROVIDER_MAP:
            msg = f"Unknown OCR provider type: {provider_type!r}"
            raise ValueError(msg)

        module_path, class_name = _PROVIDER_MAP[provider_type].rsplit(".", 1)
        module = importlib.import_module(module_path)
        klass = getattr(module, class_name)
        return klass(config)


__all__ = ["OcrProviderFactory"]
