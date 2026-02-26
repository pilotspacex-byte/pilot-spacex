"""Google Drive OAuth and file access endpoints.

Routes:
    GET    /ai/drive/status       — Connection status (200)
    GET    /ai/drive/auth-url     — OAuth authorization URL (200, 403 for guests)
    GET    /ai/drive/callback     — OAuth authorization code exchange (200)
    GET    /ai/drive/files        — List Drive files (200, 402 if not connected)
    POST   /ai/drive/import       — Import Drive file as attachment (201)
    DELETE /ai/drive/credentials  — Revoke Drive credential (204)

Feature: 020 — Chat Context Attachments & Google Drive
Source: FR-009, FR-010, FR-011, FR-012
REST contract: specs/020-chat-context-attachments/contracts/rest-api.md §4-§8
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from pilot_space.api.v1.schemas.attachments import (
    AttachmentUploadResponse,
    DriveFileListResponse,
    DriveImportRequest,
    DriveStatusResponse,
)
from pilot_space.dependencies.auth import CurrentUserId
from pilot_space.dependencies.services import DriveFileServiceDep, DriveOAuthServiceDep
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["ai-drive"])


# ---------------------------------------------------------------------------
# Standalone async functions (called directly in tests with keyword args)
# These are also registered as route handlers below.
# ---------------------------------------------------------------------------


async def get_drive_status(
    workspace_id: UUID,
    user_id: UUID,
    drive_service: Any,
) -> DriveStatusResponse:
    """Return Google Drive connection status for the workspace.

    Args:
        workspace_id: Target workspace ID.
        user_id: Authenticated user ID.
        drive_service: DriveOAuthService instance (injected or passed directly).

    Returns:
        DriveStatusResponse indicating whether Drive is connected.
    """
    return await drive_service.get_status(user_id=user_id, workspace_id=workspace_id)


async def get_drive_auth_url(
    workspace_id: UUID,
    redirect_uri: str,
    user_id: UUID,
    drive_service: Any,
    user_role: str,
) -> dict[str, str]:
    """Return a Google OAuth PKCE authorization URL.

    Args:
        workspace_id: Workspace initiating the OAuth flow.
        redirect_uri: OAuth callback URI.
        user_id: Authenticated user ID.
        drive_service: DriveOAuthService instance.
        user_role: Current user's workspace role.

    Returns:
        Dict with ``auth_url`` key containing the authorization URL.

    Raises:
        HTTPException 403: When the user has the ``guest`` role.
    """
    if user_role == "guest":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Guests cannot connect Google Drive"},
        )
    return await drive_service.get_auth_url(workspace_id=workspace_id, redirect_uri=redirect_uri)


async def list_drive_files(
    workspace_id: UUID,
    user_id: UUID,
    drive_service: Any,
    parent_id: str | None,
    search: str | None,
    page_token: str | None,
) -> DriveFileListResponse:
    """List Google Drive files for the authenticated user.

    Args:
        workspace_id: Workspace whose Drive credential to use.
        user_id: Authenticated user ID.
        drive_service: DriveFileService instance.
        parent_id: Drive folder ID to list; None for root.
        search: Optional filename filter.
        page_token: Pagination continuation token.

    Returns:
        DriveFileListResponse with a page of Drive items.
    """
    return await drive_service.list_files(
        workspace_id=workspace_id,
        user_id=user_id,
        parent_id=parent_id,
        search=search,
        page_token=page_token,
    )


async def import_drive_file(
    request: DriveImportRequest,
    user_id: UUID,
    drive_service: Any,
) -> AttachmentUploadResponse:
    """Import a Google Drive file as a chat context attachment.

    Args:
        request: Import parameters (file_id, filename, mime_type, etc.).
        user_id: Authenticated user ID.
        drive_service: DriveFileService instance.

    Returns:
        AttachmentUploadResponse with the stored attachment metadata.
    """
    return await drive_service.import_file(request=request, user_id=user_id)


async def handle_drive_callback(
    code: str,
    state: str,
    workspace_id: UUID,
    user_id: UUID,
    drive_service: Any,
) -> dict[str, str]:
    """Exchange the OAuth authorization code for tokens and persist the credential.

    Args:
        code: Authorization code from Google's redirect.
        state: CSRF state token issued by get_auth_url.
        workspace_id: Workspace the credential belongs to.
        user_id: Authenticated user owning the credential.
        drive_service: DriveOAuthService instance.

    Returns:
        Dict with ``status`` = ``"connected"``.

    Raises:
        HTTPException 400: When ``state`` is invalid or expired.
    """
    await drive_service.handle_callback(
        code=code,
        state=state,
        workspace_id=workspace_id,
        user_id=user_id,
    )
    return {"status": "connected"}


async def revoke_drive_credentials(
    workspace_id: UUID,
    user_id: UUID,
    drive_service: Any,
) -> None:
    """Revoke Google Drive access and delete the stored credential.

    Args:
        workspace_id: Target workspace ID.
        user_id: Authenticated user ID.
        drive_service: DriveOAuthService instance.
    """
    await drive_service.revoke(user_id=user_id, workspace_id=workspace_id)


# ---------------------------------------------------------------------------
# HTTP route registrations (DI-wired for production)
# ---------------------------------------------------------------------------


@router.get("/drive/status", response_model=DriveStatusResponse)
async def route_get_drive_status(  # noqa: RUF100
    workspace_id: Annotated[UUID, Query()],
    user_id: CurrentUserId,
    drive_service: DriveOAuthServiceDep,
) -> DriveStatusResponse:
    """GET /ai/drive/status — Drive connection status."""
    return await get_drive_status(
        workspace_id=workspace_id,
        user_id=user_id,
        drive_service=drive_service,
    )


@router.get("/drive/auth-url")
async def route_get_drive_auth_url(  # noqa: RUF100
    workspace_id: Annotated[UUID, Query()],
    redirect_uri: Annotated[str, Query()],
    user_id: CurrentUserId,
    drive_service: DriveOAuthServiceDep,
    user_role: Annotated[str, Query()] = "member",
) -> dict[str, str]:
    """GET /ai/drive/auth-url — OAuth authorization URL."""
    return await get_drive_auth_url(
        workspace_id=workspace_id,
        redirect_uri=redirect_uri,
        user_id=user_id,
        drive_service=drive_service,
        user_role=user_role,
    )


@router.get("/drive/files", response_model=DriveFileListResponse)
async def route_list_drive_files(  # noqa: RUF100
    workspace_id: Annotated[UUID, Query()],
    user_id: CurrentUserId,
    drive_service: DriveFileServiceDep,
    parent_id: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    page_token: Annotated[str | None, Query()] = None,
) -> DriveFileListResponse:
    """GET /ai/drive/files — List Drive files."""
    return await list_drive_files(
        workspace_id=workspace_id,
        user_id=user_id,
        drive_service=drive_service,
        parent_id=parent_id,
        search=search,
        page_token=page_token,
    )


@router.post(
    "/drive/import",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def route_import_drive_file(  # noqa: RUF100
    request: DriveImportRequest,
    user_id: CurrentUserId,
    drive_service: DriveFileServiceDep,
) -> AttachmentUploadResponse:
    """POST /ai/drive/import — Import Drive file as attachment."""
    return await import_drive_file(
        request=request,
        user_id=user_id,
        drive_service=drive_service,
    )


@router.get("/drive/callback")
async def route_handle_drive_callback(  # noqa: RUF100
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    workspace_id: Annotated[UUID, Query()],
    user_id: CurrentUserId,
    drive_service: DriveOAuthServiceDep,
) -> dict[str, str]:
    """GET /ai/drive/callback — Exchange OAuth code for tokens."""
    return await handle_drive_callback(
        code=code,
        state=state,
        workspace_id=workspace_id,
        user_id=user_id,
        drive_service=drive_service,
    )


@router.delete("/drive/credentials", status_code=status.HTTP_204_NO_CONTENT)
async def route_revoke_drive_credentials(  # noqa: RUF100
    workspace_id: Annotated[UUID, Query()],
    user_id: CurrentUserId,
    drive_service: DriveOAuthServiceDep,
) -> None:
    """DELETE /ai/drive/credentials — Revoke Drive credential."""
    await revoke_drive_credentials(
        workspace_id=workspace_id,
        user_id=user_id,
        drive_service=drive_service,
    )


__all__ = [
    "get_drive_auth_url",
    "get_drive_status",
    "handle_drive_callback",
    "import_drive_file",
    "list_drive_files",
    "revoke_drive_credentials",
    "router",
]
