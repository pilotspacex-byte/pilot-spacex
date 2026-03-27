"""Workspace OCR settings router for Pilot Space API.

Thin HTTP shell delegating to OcrConfigurationService for business logic.

Provides endpoints for managing workspace OCR provider configuration:
- GET  /workspaces/{workspace_id}/ocr/settings -- current provider info
- PUT  /workspaces/{workspace_id}/ocr/settings -- store/update provider credentials
- POST /workspaces/{workspace_id}/ocr/settings/test -- test connection

BYOK pattern: credentials are encrypted at rest via SecureKeyStorage.
Supports hunyuan_ocr (vLLM self-hosted) and tencent_ocr (Tencent Cloud SDK).

OCR-01, OCR-02, OCR-05
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request

from pilot_space.api.v1.dependencies import OcrConfigurationServiceDep
from pilot_space.api.v1.routers._workspace_admin import get_admin_workspace
from pilot_space.api.v1.schemas.workspace_ocr_settings import (
    OcrSettingsResponse,
    OcrSettingsUpdateRequest,
    OcrTestResponse,
)
from pilot_space.application.services.ocr_configuration import OcrUpdatePayload
from pilot_space.dependencies.auth import CurrentUser, DbSession
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

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
    svc: OcrConfigurationServiceDep,
) -> OcrSettingsResponse:
    """Get current OCR provider configuration for a workspace."""
    await get_admin_workspace(workspace_id, current_user, session)

    result = await svc.get_ocr_config(workspace_id)
    return OcrSettingsResponse(
        workspace_id=result.workspace_id,
        provider_type=result.provider_type,
        is_configured=result.is_configured,
        is_valid=result.is_valid,
        endpoint_url=result.endpoint_url,
        model_name=result.model_name,
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
    svc: OcrConfigurationServiceDep,
) -> OcrSettingsResponse:
    """Store or update OCR provider credentials for a workspace."""
    await get_admin_workspace(workspace_id, current_user, session)

    payload = OcrUpdatePayload(
        provider_type=body.provider_type,
        endpoint_url=body.endpoint_url,
        api_key=body.api_key,
        model_name=body.model_name,
        secret_id=body.secret_id,
        secret_key=body.secret_key,
        region=body.region,
    )
    result = await svc.update_ocr_config(workspace_id, payload)
    return OcrSettingsResponse(
        workspace_id=result.workspace_id,
        provider_type=result.provider_type,
        is_configured=result.is_configured,
        is_valid=result.is_valid,
        endpoint_url=result.endpoint_url,
        model_name=result.model_name,
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
    request: Request,
) -> OcrTestResponse:
    """Test OCR provider connection using a built-in 1x1 PNG."""
    from fastapi import HTTPException, status

    from pilot_space.ai.ocr.abstract_ocr_provider import OcrConfig
    from pilot_space.application.services.ai.ocr_service import OcrService

    await get_admin_workspace(workspace_id, current_user, session)

    _SUPPORTED_TEST_PROVIDERS = frozenset({"hunyuan_ocr", "tencent_ocr"})
    if body.provider_type not in _SUPPORTED_TEST_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot test provider_type={body.provider_type!r}",
        )

    container = request.app.state.container
    ocr_service = OcrService(master_secret=container.encryption_key())

    if body.provider_type == "hunyuan_ocr":
        config = OcrConfig(
            provider_type="hunyuan_ocr",
            endpoint_url=body.endpoint_url,
            api_key=body.api_key,
            model_name=body.model_name or "tencent/HunyuanOCR",
        )
    else:
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
        extracted_text=None,
    )


__all__ = ["router"]
