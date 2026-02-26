"""DriveFileService — Google Drive file listing and import.

Feature: 020 — Chat Context Attachments & Google Drive
Source: FR-011, FR-012
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException, status

from pilot_space.api.v1.schemas.attachments import (
    AttachmentUploadResponse,
    DriveFileItem,
    DriveFileListResponse,
)
from pilot_space.application.services.ai.attachment_upload_service import ATTACHMENT_SIZE_LIMITS
from pilot_space.infrastructure.encryption import EncryptionError, decrypt_api_key
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.api.v1.schemas.attachments import DriveImportRequest
    from pilot_space.application.services.ai.drive_oauth_service import DriveOAuthService
    from pilot_space.config import Settings
    from pilot_space.infrastructure.database.repositories.chat_attachment_repository import (
        ChatAttachmentRepository,
    )
    from pilot_space.infrastructure.database.repositories.drive_credential_repository import (
        DriveCredentialRepository,
    )
    from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
_DRIVE_EXPORT_URL = "https://www.googleapis.com/drive/v3/files/{file_id}/export"
_DRIVE_DOWNLOAD_URL = "https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

# Google Workspace MIME types → export format
_EXPORT_FORMATS: dict[str, str] = {
    "application/vnd.google-apps.document": "application/pdf",
    "application/vnd.google-apps.spreadsheet": "application/pdf",
    "application/vnd.google-apps.presentation": "application/pdf",
}

# Bucket name for chat attachment storage (must match AttachmentUploadService)
_BUCKET = "chat-attachments"

# Refresh access token 5 minutes before expiry to avoid mid-request failures
_REFRESH_BUFFER = timedelta(minutes=5)


class DriveFileService:
    """Handles Google Drive file listing and import-as-attachment operations."""

    def __init__(
        self,
        credential_repo: DriveCredentialRepository,
        attachment_repo: ChatAttachmentRepository,
        storage_client: SupabaseStorageClient,
        settings: Settings,
        oauth_service: DriveOAuthService,
    ) -> None:
        """Initialize service.

        Args:
            credential_repo: Repository for Drive credential lookup.
            attachment_repo: Repository for chat attachment persistence.
            storage_client: Supabase Storage client for file uploads.
            settings: Application settings.
            oauth_service: DriveOAuthService used for silent token refresh (FR-010).
        """
        self._credential_repo = credential_repo
        self._attachment_repo = attachment_repo
        self._storage_client = storage_client
        self._settings = settings
        self._oauth_service = oauth_service

    async def _get_valid_access_token(self, user_id: UUID, workspace_id: UUID) -> str:
        """Return a valid (non-expired) access token for the user+workspace.

        Checks token expiry and silently refreshes via DriveOAuthService when
        the token is within the refresh buffer window (5 minutes before expiry).

        Args:
            user_id: Authenticated user ID.
            workspace_id: Target workspace ID.

        Returns:
            Plaintext access token.

        Raises:
            HTTPException 402: When no credential exists.
        """
        cred = await self._credential_repo.get_by_user_workspace(user_id, workspace_id)
        if not cred:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"code": "DRIVE_NOT_CONNECTED", "message": "No Drive credential found"},
            )

        # Refresh proactively if within 5 minutes of expiry
        if cred.token_expires_at and cred.token_expires_at - datetime.now(UTC) < _REFRESH_BUFFER:
            return await self._oauth_service.refresh_access_token(user_id, workspace_id)

        try:
            return decrypt_api_key(cred.access_token)
        except EncryptionError:
            return cred.access_token

    async def list_files(
        self,
        workspace_id: UUID,
        user_id: UUID,
        session: AsyncSession | None = None,
        parent_id: str | None = None,
        search: str | None = None,
        page_token: str | None = None,
    ) -> DriveFileListResponse:
        """List files in Google Drive for the authenticated user.

        Args:
            workspace_id: Workspace whose Drive credential to use.
            user_id: Authenticated user ID.
            session: Optional database session (unused; repo manages its own).
            parent_id: Drive folder ID to list children of; None for root.
            search: Substring to filter files by name.
            page_token: Continuation token for paginated results.

        Returns:
            DriveFileListResponse with a page of Drive items.

        Raises:
            HTTPException 402: When no Drive credential exists for user+workspace.
            HTTPException 502: When the Drive API returns an error after token refresh.
        """
        access_token = await self._get_valid_access_token(user_id, workspace_id)

        params: dict[str, str] = {
            "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime,iconLink)"
        }
        q_parts: list[str] = ["trashed=false"]
        if parent_id:
            q_parts.append(f"'{parent_id}' in parents")
        if search:
            q_parts.append(f"name contains '{search}'")
        params["q"] = " and ".join(q_parts)
        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    _DRIVE_FILES_URL,
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if response.status_code == 401:
                    # Token expired between check and call — refresh once more
                    access_token = await self._oauth_service.refresh_access_token(
                        user_id, workspace_id
                    )
                    response = await client.get(
                        _DRIVE_FILES_URL,
                        params=params,
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.warning("drive_api_error", error=str(exc))
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"code": "DRIVE_API_ERROR", "message": "Drive API request failed"},
                ) from exc

        data = response.json()
        files = [
            DriveFileItem(
                id=f["id"],
                name=f["name"],
                mime_type=f["mimeType"],
                size_bytes=int(f["size"]) if "size" in f else None,
                modified_at=f.get("modifiedTime"),
                is_folder=f["mimeType"] == "application/vnd.google-apps.folder",
                icon_url=f.get("iconLink"),
            )
            for f in data.get("files", [])
        ]
        return DriveFileListResponse(files=files, next_page_token=data.get("nextPageToken"))

    async def import_file(
        self,
        request: DriveImportRequest,
        user_id: UUID,
        session: AsyncSession | None = None,
    ) -> AttachmentUploadResponse:
        """Download a Drive file and store it as a chat attachment.

        Google Workspace formats are exported as PDF before storage.
        The attachment record is persisted via the repository (not the session
        parameter, which is kept for backward compatibility only).

        Args:
            request: Import parameters including file_id and desired filename.
            user_id: Authenticated user ID.
            session: Unused; kept for API compatibility. Repo manages its own session.

        Returns:
            AttachmentUploadResponse with metadata of the stored attachment.

        Raises:
            HTTPException 402: When no Drive credential exists for user+workspace.
            HTTPException 502: When the Drive API returns an error after token refresh.
        """
        from pilot_space.infrastructure.database.models.chat_attachment import ChatAttachment

        access_token = await self._get_valid_access_token(user_id, request.workspace_id)

        mime_type = request.mime_type
        export_mime = _EXPORT_FORMATS.get(mime_type)

        async with httpx.AsyncClient() as client:
            try:
                if export_mime:
                    url = _DRIVE_EXPORT_URL.format(file_id=request.file_id)
                    response = await client.get(
                        url,
                        params={"mimeType": export_mime},
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if response.status_code == 401:
                        access_token = await self._oauth_service.refresh_access_token(
                            user_id, request.workspace_id
                        )
                        response = await client.get(
                            url,
                            params={"mimeType": export_mime},
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                    mime_type = export_mime
                else:
                    url = _DRIVE_DOWNLOAD_URL.format(file_id=request.file_id)
                    response = await client.get(
                        url, headers={"Authorization": f"Bearer {access_token}"}
                    )
                    if response.status_code == 401:
                        access_token = await self._oauth_service.refresh_access_token(
                            user_id, request.workspace_id
                        )
                        response = await client.get(
                            url, headers={"Authorization": f"Bearer {access_token}"}
                        )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.warning("drive_api_error", error=str(exc))
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"code": "DRIVE_API_ERROR", "message": "Drive API request failed"},
                ) from exc

        file_data = response.content

        # Enforce per-type size limits after download (spec §7: 400 FILE_TOO_LARGE)
        size_limit = ATTACHMENT_SIZE_LIMITS.get(mime_type)
        if size_limit is not None and len(file_data) > size_limit:
            limit_mb = size_limit // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "FILE_TOO_LARGE",
                    "message": f"File exceeds {limit_mb}MB limit for {mime_type}",
                },
            )

        # Use one UUID for both storage key and attachment id (spec data-model.md)
        attachment_id = uuid4()
        storage_key = (
            f"{_BUCKET}/{request.workspace_id}/{user_id}/{attachment_id}/{request.filename}"
        )
        await self._storage_client.upload_object(
            bucket=_BUCKET,
            key=storage_key,
            data=file_data,
            content_type=mime_type,
        )

        expires_at = datetime.now(UTC) + timedelta(hours=24)
        attachment = ChatAttachment(
            id=attachment_id,
            user_id=user_id,
            workspace_id=request.workspace_id,
            session_id=request.session_id,
            filename=request.filename,
            mime_type=mime_type,
            size_bytes=len(file_data),
            source="google_drive",
            storage_key=storage_key,
            expires_at=expires_at,
            drive_file_id=request.file_id,
        )

        persisted = await self._attachment_repo.create(attachment)

        return AttachmentUploadResponse(
            attachment_id=persisted.id,
            filename=persisted.filename,
            mime_type=persisted.mime_type,
            size_bytes=persisted.size_bytes,
            source="google_drive",
            expires_at=persisted.expires_at,
        )


__all__ = ["DriveFileService"]
