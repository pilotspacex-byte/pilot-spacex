"""Workspace OCR settings router for Pilot Space API.

Provides endpoints for managing workspace OCR provider configuration:
- GET  /workspaces/{workspace_id}/ocr/settings — current provider info
- PUT  /workspaces/{workspace_id}/ocr/settings — store/update provider credentials
- POST /workspaces/{workspace_id}/ocr/settings/test — test connection

BYOK pattern: credentials are encrypted at rest via SecureKeyStorage.
Supports hunyuan_ocr (vLLM self-hosted) and tencent_ocr (Tencent Cloud SDK).

OCR-01, OCR-02, OCR-05
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
from pilot_space.application.services.ai.ocr_service import OcrService
from pilot_space.config import get_settings
from pilot_space.dependencies import CurrentUser, DbSession
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

_SUPPORTED_OCR_PROVIDERS = frozenset({"hunyuan_ocr", "tencent_ocr", "none"})


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


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

# Minimal 1x1 white PNG used for connection tests (base64-decoded at runtime)
_TEST_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


async def _get_admin_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> None:
    """Resolve workspace and verify admin access.

    Raises:
        HTTPException 404 if workspace not found.
        HTTPException 403 if user is not an admin.
    """
    workspace_repo = WorkspaceRepository(session=session)
    workspace = await workspace_repo.get_with_members(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not member or not member.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{workspace_id}/ocr/settings",
    response_model=OcrSettingsResponse,
    tags=["workspaces", "OCR Settings"],
)
async def get_ocr_settings(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> OcrSettingsResponse:
    """Get current OCR provider configuration for a workspace.

    Returns provider type, configuration status, and endpoint URL (no key material).
    Requires workspace admin permission.
    """
    await _get_admin_workspace(workspace_id, current_user, session)

    settings = get_settings()
    key_storage = SecureKeyStorage(
        db=session, master_secret=settings.encryption_key.get_secret_value()
    )

    # Check dedicated OCR providers in priority order
    for ocr_provider in ("hunyuan_ocr", "tencent_ocr"):
        info = await key_storage.get_key_info(workspace_id, ocr_provider, "ocr")
        if info:
            return OcrSettingsResponse(
                workspace_id=workspace_id,
                provider_type=ocr_provider,
                is_configured=True,
                is_valid=info.is_valid,
                endpoint_url=info.base_url,
                model_name=info.model_name,
            )

    return OcrSettingsResponse(
        workspace_id=workspace_id,
        provider_type="none",
        is_configured=False,
        is_valid=None,
        endpoint_url=None,
        model_name=None,
    )


@router.put(
    "/{workspace_id}/ocr/settings",
    response_model=OcrSettingsResponse,
    tags=["workspaces", "OCR Settings"],
)
async def update_ocr_settings(
    workspace_id: UUID,
    body: OcrSettingsUpdateRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> OcrSettingsResponse:
    """Store or update OCR provider credentials for a workspace.

    For provider_type="none", deletes all OCR provider keys.
    Requires workspace admin permission.
    """
    await _get_admin_workspace(workspace_id, current_user, session)

    if body.provider_type not in _SUPPORTED_OCR_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported provider_type: {body.provider_type!r}. "
            f"Allowed: {sorted(_SUPPORTED_OCR_PROVIDERS)}",
        )

    settings = get_settings()
    key_storage = SecureKeyStorage(
        db=session, master_secret=settings.encryption_key.get_secret_value()
    )

    if body.provider_type == "none":
        # Delete all OCR provider keys for this workspace
        for ocr_provider in ("hunyuan_ocr", "tencent_ocr"):
            await key_storage.delete_api_key(workspace_id, ocr_provider, "ocr")

        logger.info("ocr_settings_cleared", workspace_id=str(workspace_id))
        return OcrSettingsResponse(
            workspace_id=workspace_id,
            provider_type="none",
            is_configured=False,
            is_valid=None,
            endpoint_url=None,
            model_name=None,
        )

    if body.provider_type == "hunyuan_ocr":
        await key_storage.store_api_key(
            workspace_id=workspace_id,
            provider="hunyuan_ocr",
            service_type="ocr",
            api_key=body.api_key,
            base_url=body.endpoint_url,
            model_name=body.model_name or "tencent/HunyuanOCR",
        )
        logger.info(
            "ocr_settings_updated",
            workspace_id=str(workspace_id),
            provider="hunyuan_ocr",
        )
        info = await key_storage.get_key_info(workspace_id, "hunyuan_ocr", "ocr")
        return OcrSettingsResponse(
            workspace_id=workspace_id,
            provider_type="hunyuan_ocr",
            is_configured=True,
            is_valid=info.is_valid if info else None,
            endpoint_url=body.endpoint_url,
            model_name=body.model_name or "tencent/HunyuanOCR",
        )

    # tencent_ocr: encode secret_id + secret_key as JSON blob in encrypted_key;
    # region stored in model_name column for retrieval.
    if body.provider_type == "tencent_ocr":
        credentials_json: str | None = None
        if body.secret_id and body.secret_key:
            credentials_json = json.dumps({"id": body.secret_id, "key": body.secret_key})

        await key_storage.store_api_key(
            workspace_id=workspace_id,
            provider="tencent_ocr",
            service_type="ocr",
            api_key=credentials_json,
            base_url=None,
            model_name=body.region or "ap-guangzhou",
        )
        logger.info(
            "ocr_settings_updated",
            workspace_id=str(workspace_id),
            provider="tencent_ocr",
        )
        info = await key_storage.get_key_info(workspace_id, "tencent_ocr", "ocr")
        return OcrSettingsResponse(
            workspace_id=workspace_id,
            provider_type="tencent_ocr",
            is_configured=True,
            is_valid=info.is_valid if info else None,
            endpoint_url=None,
            model_name=body.region or "ap-guangzhou",
        )

    # Should not be reachable but keeps pyright happy
    raise HTTPException(  # pragma: no cover
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unhandled provider_type: {body.provider_type!r}",
    )


@router.post(
    "/{workspace_id}/ocr/settings/test",
    response_model=OcrTestResponse,
    tags=["workspaces", "OCR Settings"],
)
async def test_ocr_connection(
    workspace_id: UUID,
    body: OcrSettingsUpdateRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> OcrTestResponse:
    """Test OCR provider connection using a built-in 1x1 PNG.

    Instantiates the provider with the supplied credentials (without storing them)
    and calls validate_connection(). Returns success/error status.
    Requires workspace admin permission.
    """
    await _get_admin_workspace(workspace_id, current_user, session)

    if body.provider_type not in _SUPPORTED_OCR_PROVIDERS - {"none"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot test provider_type={body.provider_type!r}",
        )

    from pilot_space.ai.ocr.abstract_ocr_provider import OcrConfig

    settings = get_settings()
    ocr_service = OcrService(master_secret=settings.encryption_key.get_secret_value())

    if body.provider_type == "hunyuan_ocr":
        config = OcrConfig(
            provider_type="hunyuan_ocr",
            endpoint_url=body.endpoint_url,
            api_key=body.api_key,
            model_name=body.model_name or "tencent/HunyuanOCR",
        )
    else:
        # tencent_ocr — decode credentials
        config = OcrConfig(
            provider_type="tencent_ocr",
            secret_id=body.secret_id,
            secret_key=body.secret_key,
            region=body.region or "ap-guangzhou",
        )

    is_valid, error_msg = await ocr_service.validate_connection(body.provider_type, config)

    return OcrTestResponse(
        success=is_valid,
        error=error_msg,
        extracted_text=None,  # validate_connection() does not extract text
    )


__all__ = ["router"]
