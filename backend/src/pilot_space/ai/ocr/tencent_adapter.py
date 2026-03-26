"""TencentCloud OCR adapter — GeneralAccurateOCR via SDK."""

from __future__ import annotations

import asyncio
import base64

try:
    from tencentcloud.common.credential import Credential  # type: ignore[import-untyped]
    from tencentcloud.ocr.v20181119 import models as ocr_models  # type: ignore[import-untyped]
    from tencentcloud.ocr.v20181119.ocr_client import OcrClient  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover
    Credential = None  # type: ignore[assignment,misc]
    OcrClient = None  # type: ignore[assignment]
    ocr_models = None  # type: ignore[assignment]

from pilot_space.infrastructure.logging import get_logger

from .abstract_ocr_provider import AbstractOcrProvider, OcrConfig, OcrResult

logger = get_logger(__name__)

# 1x1 transparent PNG for connection validation
_TEST_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhf"
    "DwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class TencentCloudOcrAdapter(AbstractOcrProvider):
    """Adapter for Tencent Cloud OCR API using GeneralAccurateOCR.

    Credentials come from OcrConfig.secret_id / secret_key and region.
    Calls are dispatched via asyncio.get_event_loop().run_in_executor so
    the synchronous SDK never blocks the uvicorn event loop.
    """

    def __init__(self, config: OcrConfig) -> None:
        self._config = config

    def _build_client(self) -> object:
        """Construct a Tencent OCR client from config credentials."""
        if Credential is None or OcrClient is None:
            raise RuntimeError(
                "tencentcloud-sdk-python-ocr is not installed. "
                "Install with: pip install tencentcloud-sdk-python-ocr"
            )
        cred = Credential(self._config.secret_id, self._config.secret_key)  # type: ignore[operator]
        return OcrClient(cred, self._config.region)  # type: ignore[operator]

    async def extract(
        self,
        image_data: bytes,
        mime_type: str,
        prompt: str | None = None,
    ) -> OcrResult:
        """Extract text via TencentCloud GeneralAccurateOCR.

        Uses run_in_executor to avoid blocking the event loop with the
        synchronous Tencent SDK call.
        """
        client = self._build_client()

        req = ocr_models.GeneralAccurateOCRRequest()  # type: ignore[union-attr]
        req.ImageBase64 = base64.b64encode(image_data).decode()

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, client.GeneralAccurateOCR, req)  # type: ignore[attr-defined]

        lines = [det.DetectedText for det in resp.TextDetections]
        text = "\n".join(lines)

        logger.debug(
            "TencentCloud OCR extraction complete",
            line_count=len(lines),
        )

        return OcrResult(
            text=text,
            confidence=0.0,  # Tencent API doesn't return single confidence score
            provider_used="tencent_ocr",
        )

    async def validate_connection(self) -> tuple[bool, str | None]:
        """Verify the Tencent Cloud OCR credentials using a 1x1 test PNG."""
        test_data = base64.b64decode(_TEST_PNG_B64)
        try:
            await self.extract(test_data, "image/png")
            return True, None
        except Exception as exc:
            logger.warning("TencentCloud OCR connection validation failed", error=str(exc))
            return False, str(exc)


__all__ = ["TencentCloudOcrAdapter"]
