"""Pydantic schemas for workspace OCR settings API.

OCR-01, OCR-02, OCR-05: BYOK OCR provider configuration schemas.
Supports hunyuan_ocr (vLLM self-hosted) and tencent_ocr (Tencent Cloud SDK).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class OcrSettingsResponse(BaseModel):
    """Current OCR provider settings for a workspace."""

    workspace_id: UUID
    provider_type: str  # "hunyuan_ocr" | "tencent_ocr" | "none"
    is_configured: bool
    is_valid: bool | None
    endpoint_url: str | None  # Masked or full URL (no key material)
    model_name: str | None


class OcrSettingsUpdateRequest(BaseModel):
    """Request body for PUT /workspaces/{id}/ocr/settings."""

    provider_type: str  # "hunyuan_ocr" | "tencent_ocr" | "none"
    # HunyuanOCR fields
    endpoint_url: str | None = None
    api_key: str | None = None
    model_name: str | None = None
    # TencentCloud fields
    secret_id: str | None = None
    secret_key: str | None = None
    region: str | None = None


class OcrTestResponse(BaseModel):
    """Result of POST /workspaces/{id}/ocr/settings/test."""

    success: bool
    error: str | None
    extracted_text: str | None


__all__ = [
    "OcrSettingsResponse",
    "OcrSettingsUpdateRequest",
    "OcrTestResponse",
]
