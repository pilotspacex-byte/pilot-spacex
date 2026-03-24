"""GPT-4o Vision OCR adapter — OpenAI gpt-4o for image text extraction."""

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


class Gpt4oVisionAdapter(AbstractOcrProvider):
    """Adapter for GPT-4o vision-based OCR extraction.

    Uses gpt-4o by default (configurable via OcrConfig.model_name).
    The openai_client is injected to allow test mocking without hitting
    the real OpenAI API.
    """

    def __init__(self, config: OcrConfig, openai_client: Any = None) -> None:
        self._config = config
        self._client = openai_client  # None means lazy-create on first call

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self._config.api_key)
        return self._client

    async def extract(
        self,
        image_data: bytes,
        mime_type: str,
        prompt: str | None = None,
    ) -> OcrResult:
        """Extract text via GPT-4o vision API."""
        b64 = base64.b64encode(image_data).decode()
        data_uri = f"data:{mime_type};base64,{b64}"

        response = await self._get_client().chat.completions.create(
            model=self._config.model_name,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        },
                        {
                            "type": "text",
                            "text": prompt or "Extract all text from this image.",
                        },
                    ],
                },
            ],
        )

        raw_text: str = response.choices[0].message.content
        confidence, clean_text = parse_confidence(raw_text)

        logger.debug(
            "GPT-4o vision OCR extraction complete",
            confidence=confidence,
            text_length=len(clean_text),
        )

        return OcrResult(
            text=clean_text,
            confidence=confidence,
            provider_used="gpt4o_vision",
        )

    async def validate_connection(self) -> tuple[bool, str | None]:
        """Verify the OpenAI API key is valid using a 1x1 test PNG."""
        test_data = base64.b64decode(_TEST_PNG_B64)
        try:
            await self.extract(test_data, "image/png", "Test connection.")
            return True, None
        except Exception as exc:
            logger.warning("GPT-4o vision connection validation failed", error=str(exc))
            return False, str(exc)


__all__ = ["Gpt4oVisionAdapter"]
