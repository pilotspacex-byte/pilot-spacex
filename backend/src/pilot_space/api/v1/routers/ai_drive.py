"""Google Drive OAuth and file access endpoints.

Routes:
    GET    /ai/drive/status       — Connection status (200)
    GET    /ai/drive/auth-url     — OAuth authorization URL (200, 403 for guests)
    GET    /ai/drive/callback     — OAuth authorization code exchange (302 redirect)
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
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from pilot_space.api.v1.schemas.attachments import (
    AttachmentUploadResponse,
    DriveFileListResponse,
    DriveImportRequest,
    DriveStatusResponse,
)
from pilot_space.config import Settings, get_settings
from pilot_space.dependencies.auth import CurrentUserId, DbSession
from pilot_space.dependencies.services import DriveFileServiceDep, DriveOAuthServiceDep
from pilot_space.domain.exceptions import ForbiddenError
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["ai-drive"])

SettingsDep = Annotated[Settings, get_settings]


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
        raise ForbiddenError("Guests cannot connect Google Drive")
    return await drive_service.get_auth_url(
        workspace_id=workspace_id,
        redirect_uri=redirect_uri,
        user_id=user_id,
    )


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
    drive_service: Any,
) -> str:
    """Exchange the OAuth authorization code for tokens and persist the credential.

    The user_id and workspace_id are extracted from the PKCE state registry —
    no JWT is required (Google does not send one on redirect).

    Args:
        code: Authorization code from Google's redirect.
        state: CSRF state token issued by get_auth_url.
        drive_service: DriveOAuthService instance.

    Returns:
        workspace_id as string (used by caller to build redirect URL).

    Raises:
        HTTPException 400: When ``state`` is invalid or expired.
    """
    return await drive_service.handle_callback(code=code, state=state)


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
    db: DbSession,
) -> dict[str, str]:
    """GET /ai/drive/auth-url — OAuth authorization URL.

    Fetches the caller's actual workspace role from the database.
    Never trusts a caller-supplied role parameter.
    """
    # Fetch actual role from DB — never trust caller-supplied role
    result = await db.execute(
        select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    role = result.scalar()
    return await get_drive_auth_url(
        workspace_id=workspace_id,
        redirect_uri=redirect_uri,
        user_id=user_id,
        drive_service=drive_service,
        user_role=str(role.value).lower() if role else "guest",
    )


@router.get("/drive/callback")
async def route_handle_drive_callback(  # noqa: RUF100
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    drive_service: DriveOAuthServiceDep,
) -> RedirectResponse:
    """GET /ai/drive/callback — Exchange OAuth code for tokens, redirect to frontend.

    Auth: None — Google's redirect does not carry a JWT Bearer token.
    On success: redirects to {frontend_url}?drive_connected=true&workspace_id={id}
    On error: redirects to {frontend_url}?drive_error={code}
    """
    settings = get_settings()
    try:
        workspace_id_str = await handle_drive_callback(
            code=code,
            state=state,
            drive_service=drive_service,
        )
        redirect_url = (
            f"{settings.frontend_url}?drive_connected=true&workspace_id={workspace_id_str}"
        )
        return RedirectResponse(url=redirect_url, status_code=302)
    except HTTPException as exc:
        error_code = (
            exc.detail.get("code", "OAUTH_ERROR") if isinstance(exc.detail, dict) else "OAUTH_ERROR"
        )
        redirect_url = f"{settings.frontend_url}?drive_error={error_code}"
        return RedirectResponse(url=redirect_url, status_code=302)


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
    "route_get_drive_auth_url",
    "router",
]
