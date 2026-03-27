"""OCR configuration service for workspace OCR provider management.

Handles OCR provider selection, credential storage, and connection testing.
Extracted from workspace_ocr_settings.py router to enforce thin-router pattern.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.domain.exceptions import ValidationError as DomainValidationError
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage

logger = get_logger(__name__)

_SUPPORTED_OCR_PROVIDERS = frozenset({"hunyuan_ocr", "tencent_ocr", "none"})


@dataclass
class OcrConfigResult:
    """Result of getting OCR configuration."""

    workspace_id: UUID
    provider_type: str
    is_configured: bool
    is_valid: bool | None
    endpoint_url: str | None
    model_name: str | None


@dataclass
class OcrUpdatePayload:
    """Input for updating OCR settings."""

    provider_type: str
    endpoint_url: str | None = None
    api_key: str | None = None
    model_name: str | None = None
    secret_id: str | None = None
    secret_key: str | None = None
    region: str | None = None


class OcrConfigurationService:
    """Manages workspace OCR provider configuration.

    Handles:
    - Reading current OCR provider settings
    - Storing/updating OCR provider credentials
    - Provider type validation

    Args:
        key_storage: Secure key storage for credential encryption.
    """

    def __init__(self, key_storage: SecureKeyStorage) -> None:
        self._key_storage = key_storage

    async def get_ocr_config(self, workspace_id: UUID) -> OcrConfigResult:
        """Get current OCR provider configuration for a workspace."""
        for ocr_provider in ("hunyuan_ocr", "tencent_ocr"):
            info = await self._key_storage.get_key_info(workspace_id, ocr_provider, "ocr")
            if info:
                return OcrConfigResult(
                    workspace_id=workspace_id,
                    provider_type=ocr_provider,
                    is_configured=True,
                    is_valid=info.is_valid,
                    endpoint_url=info.base_url,
                    model_name=info.model_name,
                )

        return OcrConfigResult(
            workspace_id=workspace_id,
            provider_type="none",
            is_configured=False,
            is_valid=None,
            endpoint_url=None,
            model_name=None,
        )

    async def update_ocr_config(
        self, workspace_id: UUID, payload: OcrUpdatePayload
    ) -> OcrConfigResult:
        """Store or update OCR provider credentials for a workspace.

        Raises:
            DomainValidationError: If provider_type is unsupported or required fields missing.
        """
        if payload.provider_type not in _SUPPORTED_OCR_PROVIDERS:
            raise DomainValidationError(
                f"Unsupported provider_type: {payload.provider_type!r}. "
                f"Allowed: {sorted(_SUPPORTED_OCR_PROVIDERS)}"
            )

        if payload.provider_type == "none":
            for ocr_provider in ("hunyuan_ocr", "tencent_ocr"):
                await self._key_storage.delete_api_key(workspace_id, ocr_provider, "ocr")
            logger.info("ocr_settings_cleared", workspace_id=str(workspace_id))
            return OcrConfigResult(
                workspace_id=workspace_id,
                provider_type="none",
                is_configured=False,
                is_valid=None,
                endpoint_url=None,
                model_name=None,
            )

        if payload.provider_type == "hunyuan_ocr":
            if not payload.endpoint_url:
                raise DomainValidationError("endpoint_url is required for hunyuan_ocr")
            await self._key_storage.store_api_key(
                workspace_id=workspace_id,
                provider="hunyuan_ocr",
                service_type="ocr",
                api_key=payload.api_key,
                base_url=payload.endpoint_url,
                model_name=payload.model_name or "tencent/HunyuanOCR",
            )
            logger.info(
                "ocr_settings_updated",
                workspace_id=str(workspace_id),
                provider="hunyuan_ocr",
            )
            info = await self._key_storage.get_key_info(workspace_id, "hunyuan_ocr", "ocr")
            return OcrConfigResult(
                workspace_id=workspace_id,
                provider_type="hunyuan_ocr",
                is_configured=True,
                is_valid=info.is_valid if info else None,
                endpoint_url=payload.endpoint_url,
                model_name=payload.model_name or "tencent/HunyuanOCR",
            )

        if payload.provider_type == "tencent_ocr":
            if not payload.secret_id or not payload.secret_key:
                raise DomainValidationError("secret_id and secret_key are required for tencent_ocr")
            credentials_json: str | None = None
            if payload.secret_id and payload.secret_key:
                credentials_json = json.dumps({"id": payload.secret_id, "key": payload.secret_key})

            await self._key_storage.store_api_key(
                workspace_id=workspace_id,
                provider="tencent_ocr",
                service_type="ocr",
                api_key=credentials_json,
                base_url=None,
                model_name=payload.region or "ap-guangzhou",
            )
            logger.info(
                "ocr_settings_updated",
                workspace_id=str(workspace_id),
                provider="tencent_ocr",
            )
            info = await self._key_storage.get_key_info(workspace_id, "tencent_ocr", "ocr")
            return OcrConfigResult(
                workspace_id=workspace_id,
                provider_type="tencent_ocr",
                is_configured=True,
                is_valid=info.is_valid if info else None,
                endpoint_url=None,
                model_name=payload.region or "ap-guangzhou",
            )

        raise DomainValidationError(f"Unhandled provider_type: {payload.provider_type!r}")

    def list_providers(self) -> list[str]:
        """Return list of supported OCR provider types."""
        return sorted(_SUPPORTED_OCR_PROVIDERS)
