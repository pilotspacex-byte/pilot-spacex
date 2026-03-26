"""HunyuanOCR adapter — vLLM HTTP /v1/chat/completions endpoint."""

from __future__ import annotations

import base64

import httpx

from pilot_space.infrastructure.logging import get_logger

from .abstract_ocr_provider import AbstractOcrProvider, OcrConfig, OcrResult, parse_confidence

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are an OCR assistant. Extract all text from the image preserving the original layout. "
    "Output tables as markdown tables. Output lists as markdown lists. "
    "Indicate confidence as a float between 0 and 1 on the last line in format: CONFIDENCE:0.95"
)

# 1x1 transparent PNG for connection validation
_TEST_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhf"
    "DwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class HunyuanOcrAdapter(AbstractOcrProvider):
    """Adapter for Tencent HunyuanOCR via vLLM HTTP endpoint.

    Sends image as an image_url content block to the OpenAI-compatible
    /v1/chat/completions API exposed by vLLM.
    """

    def __init__(self, config: OcrConfig) -> None:
        self._config = config

    async def extract(
        self,
        image_data: bytes,
        mime_type: str,
        prompt: str | None = None,
    ) -> OcrResult:
        """Extract text from image via HunyuanOCR vLLM endpoint."""
        b64 = base64.b64encode(image_data).decode()
        data_uri = f"data:{mime_type};base64,{b64}"

        payload = {
            "model": self._config.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_uri}},
                        {
                            "type": "text",
                            "text": prompt or "Extract all text from this image.",
                        },
                    ],
                },
            ],
            "max_tokens": 4096,
        }

        headers: dict[str, str] = {}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        base_url = (self._config.endpoint_url or "").rstrip("/")
        chat_url = (
            f"{base_url}/chat/completions"
            if base_url.endswith("/v1")
            else f"{base_url}/v1/chat/completions"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                chat_url,
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()

        raw_text: str = resp.json()["choices"][0]["message"]["content"]
        confidence, clean_text = parse_confidence(raw_text)

        logger.debug(
            "HunyuanOCR extraction complete",
            confidence=confidence,
            text_length=len(clean_text),
        )

        return OcrResult(
            text=clean_text,
            confidence=confidence,
            provider_used="hunyuan_ocr",
        )

    async def validate_connection(self) -> tuple[bool, str | None]:
        """Verify the vLLM endpoint is reachable using a 1x1 test PNG."""
        test_data = base64.b64decode(_TEST_PNG_B64)
        try:
            await self.extract(test_data, "image/png", "Test connection.")
            return True, None
        except Exception as exc:
            logger.warning("HunyuanOCR connection validation failed", error=str(exc))
            return False, str(exc)


__all__ = ["HunyuanOcrAdapter"]
