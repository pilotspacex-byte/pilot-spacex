"""OcrService — cascade fallback OCR orchestrator.

Implements DD-003 compliant BYOK pattern: no data leaves infra on the primary
path (HunyuanOCR runs self-hosted via vLLM). Falls back to Claude vision and
GPT-4o vision if the primary provider is unavailable.

Feature: OCR-01, OCR-02, OCR-05
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
from pilot_space.ai.ocr.abstract_ocr_provider import OcrConfig, OcrResult
from pilot_space.ai.ocr.factory import OcrProviderFactory
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.ocr.abstract_ocr_provider import AbstractOcrProvider

logger = get_logger(__name__)


async def is_scanned_pdf(data: bytes) -> bool:
    """Return True if a PDF has fewer than 100 chars of embedded text (likely scanned).

    Args:
        data: Raw PDF bytes.

    Returns:
        True if the PDF appears to be a scanned document (no/minimal text layer),
        False if sufficient embedded text was found.
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        text = "".join(page.extract_text() or "" for page in reader.pages)
        return len(text.strip()) < 100
    except Exception:
        # If we can't determine, assume scanned (safer to run OCR)
        return True


class OcrService:
    """Cascade fallback OCR orchestrator.

    Builds a provider chain at extraction time based on workspace key config:
    1. Dedicated OCR provider (HunyuanOCR / TencentCloud) — self-hosted, primary
    2. Claude vision fallback — reuses existing Anthropic LLM key
    3. (Future) GPT-4o vision fallback — reuses existing OpenAI key

    On all failures, returns OcrResult(text='', provider_used='none') without raising.

    Example:
        service = OcrService(master_secret=settings.encryption_key.get_secret_value())
        result = await service.extract_with_fallback(
            image_data=bytes_data,
            mime_type="image/png",
            workspace_id=workspace_id,
            attachment_id=attachment_id,
            session=db_session,
        )
    """

    def __init__(self, master_secret: str) -> None:
        """Initialise the OCR service.

        Args:
            master_secret: Master encryption secret used to decrypt stored API keys.
        """
        self._master_secret = master_secret

    async def extract_with_fallback(
        self,
        image_data: bytes,
        mime_type: str,
        workspace_id: UUID,
        attachment_id: UUID | None,
        session: AsyncSession,
    ) -> OcrResult:
        """Try each provider in the fallback chain, return the first successful result.

        Args:
            image_data: Raw image/PDF bytes to process.
            mime_type: MIME type of the content (e.g. "image/png", "application/pdf").
            workspace_id: Workspace UUID used to look up stored provider credentials.
            attachment_id: FK to chat_attachments; stored in ocr_results for traceability.
            session: Async database session for key lookups and result persistence.

        Returns:
            OcrResult from the first successful provider, or
            OcrResult(text='', provider_used='none') if all providers fail.
        """
        providers = await self._build_fallback_chain(workspace_id, session)
        for provider in providers:
            result: OcrResult | None = None
            try:
                result = await provider.extract(image_data, mime_type)
                logger.debug("ocr_provider_used", provider=result.provider_used)
            except Exception as exc:
                logger.debug(
                    "ocr_provider_failed",
                    provider=type(provider).__name__,
                    error=str(exc),
                )
                continue

            await self._persist_result(result, attachment_id, session)
            return result

        return OcrResult(text="", provider_used="none")

    async def _build_fallback_chain(
        self,
        workspace_id: UUID,
        session: AsyncSession,
    ) -> list[AbstractOcrProvider]:
        """Build ordered provider list: configured OCR provider → Claude vision.

        Args:
            workspace_id: Workspace UUID for credential lookup.
            session: Async database session.

        Returns:
            Ordered list of AbstractOcrProvider instances; may be empty.
        """
        storage = SecureKeyStorage(db=session, master_secret=self._master_secret)
        chain: list[AbstractOcrProvider] = []

        # 1. Dedicated OCR provider (hunyuan_ocr first, then tencent_ocr)
        for ocr_provider in ("hunyuan_ocr", "tencent_ocr"):
            info = await storage.get_key_info(workspace_id, ocr_provider, "ocr")
            if info:
                api_key = await storage.get_api_key(workspace_id, ocr_provider, "ocr")
                if ocr_provider == "tencent_ocr" and api_key:
                    # Tencent credentials stored as JSON: {"id": "...", "key": "..."}
                    import json

                    creds = json.loads(api_key)
                    config = OcrConfig(
                        provider_type=ocr_provider,
                        secret_id=creds.get("id"),
                        secret_key=creds.get("key"),
                        region=info.model_name or "ap-guangzhou",
                    )
                else:
                    config = OcrConfig(
                        provider_type=ocr_provider,
                        endpoint_url=info.base_url,
                        api_key=api_key,
                        model_name=info.model_name or "tencent/HunyuanOCR",
                    )
                chain.append(OcrProviderFactory.create(ocr_provider, config))
                break  # Only one dedicated OCR provider active at a time

        # 2. Claude vision fallback — reuses existing Anthropic LLM key
        claude_key = await storage.get_api_key(workspace_id, "anthropic", "llm")
        if claude_key:
            chain.append(
                OcrProviderFactory.create(
                    "claude_vision",
                    OcrConfig(provider_type="claude_vision", api_key=claude_key),
                )
            )

        return chain

    async def _persist_result(
        self,
        result: OcrResult,
        attachment_id: UUID | None,
        session: AsyncSession,
    ) -> None:
        """Persist OCR extraction result to the ocr_results table.

        Args:
            result: OcrResult from a successful extraction.
            attachment_id: FK to chat_attachments (nullable after 24h TTL cleanup).
            session: Async database session.
        """
        from pilot_space.infrastructure.database.models.ocr_result import OcrResultModel

        row = OcrResultModel(
            attachment_id=attachment_id,
            extracted_text=result.text,
            tables_json=(
                [
                    {
                        "markdown": t.markdown,
                        "row_count": t.row_count,
                        "col_count": t.col_count,
                    }
                    for t in result.tables
                ]
                if result.tables
                else None
            ),
            confidence=result.confidence,
            language=result.language if result.language not in ("", "unknown") else None,
            provider_used=result.provider_used,
        )
        session.add(row)
        await session.flush()  # Caller owns commit

    async def validate_connection(
        self,
        provider_type: str,
        config: OcrConfig,
    ) -> tuple[bool, str | None]:
        """Validate connectivity and credentials for a given OCR provider config.

        Args:
            provider_type: Provider slug (e.g. "hunyuan_ocr", "tencent_ocr").
            config: Provider credentials and endpoint.

        Returns:
            Tuple of (is_valid, error_message). error_message is None on success.
        """
        provider = OcrProviderFactory.create(provider_type, config)
        return await provider.validate_connection()


__all__ = ["OcrService", "is_scanned_pdf"]
