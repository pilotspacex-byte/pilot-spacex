"""Claude Vision OCR adapter — Anthropic claude-3-5-haiku for image text extraction."""

from __future__ import annotations

import base64
from typing import Any

from pilot_space.infrastructure.logging import get_logger

from .abstract_ocr_provider import AbstractOcrProvider, OcrConfig, OcrResult, parse_confidence
from .hunyuan_adapter import SYSTEM_PROMPT

logger = get_logger(__name__)

# 1x1 transparent PNG for connection validation
_TEST_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhf"
    "DwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

_DEFAULT_MODEL = "claude-3-5-haiku-20241022"


class ClaudeVisionAdapter(AbstractOcrProvider):
    """Adapter for Claude vision-based OCR extraction.

    Uses claude-3-5-haiku as a fast, cost-efficient fallback model.
    The anthropic_client is injected to allow test mocking without
    touching the real API.
    """

    def __init__(self, config: OcrConfig, anthropic_client: Any = None) -> None:
        self._config = config
        self._client = anthropic_client  # None means lazy-create on first call

    def _get_client(self) -> Any:
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self._config.api_key)
        return self._client

    async def extract(
        self,
        image_data: bytes,
        mime_type: str,
        prompt: str | None = None,
    ) -> OcrResult:
        """Extract text via Claude vision API."""
        b64 = base64.b64encode(image_data).decode()

        response = await self._get_client().messages.create(
            model=_DEFAULT_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt or "Extract all text from this image.",
                        },
                    ],
                }
            ],
        )

        raw_text: str = response.content[0].text
        confidence, clean_text = parse_confidence(raw_text)

        logger.debug(
            "Claude vision OCR extraction complete",
            confidence=confidence,
            text_length=len(clean_text),
        )

        return OcrResult(
            text=clean_text,
            confidence=confidence,
            provider_used="claude_vision",
        )

    async def validate_connection(self) -> tuple[bool, str | None]:
        """Verify the Anthropic API key is valid using a 1x1 test PNG."""
        test_data = base64.b64decode(_TEST_PNG_B64)
        try:
            await self.extract(test_data, "image/png", "Test connection.")
            return True, None
        except Exception as exc:
            logger.warning("Claude vision connection validation failed", error=str(exc))
            return False, str(exc)


__all__ = ["ClaudeVisionAdapter"]
