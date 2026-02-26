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
from pilot_space.infrastructure.encryption import EncryptionError, decrypt_api_key
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.api.v1.schemas.attachments import DriveImportRequest
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


class DriveFileService:
    """Handles Google Drive file listing and import-as-attachment operations."""

    def __init__(
        self,
        credential_repo: DriveCredentialRepository,
        attachment_repo: ChatAttachmentRepository,
        storage_client: SupabaseStorageClient,
        settings: Settings,
    ) -> None:
        """Initialize service.

        Args:
            credential_repo: Repository for Drive credential lookup.
            attachment_repo: Repository for chat attachment persistence.
            storage_client: Supabase Storage client for file uploads.
            settings: Application settings.
        """
        self._credential_repo = credential_repo
        self._attachment_repo = attachment_repo
        self._storage_client = storage_client
        self._settings = settings

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
        """
        cred = await self._credential_repo.get_by_user_workspace(user_id, workspace_id)
        if not cred:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"code": "DRIVE_NOT_CONNECTED", "message": "No Drive credential found"},
            )

        try:
            access_token = decrypt_api_key(cred.access_token)
        except EncryptionError:
            access_token = cred.access_token

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
            response = await client.get(
                _DRIVE_FILES_URL,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
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
        """
        from pilot_space.infrastructure.database.models.chat_attachment import ChatAttachment

        cred = await self._credential_repo.get_by_user_workspace(user_id, request.workspace_id)
        if not cred:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"code": "DRIVE_NOT_CONNECTED", "message": "No Drive credential found"},
            )

        try:
            access_token = decrypt_api_key(cred.access_token)
        except EncryptionError:
            access_token = cred.access_token

        mime_type = request.mime_type
        export_mime = _EXPORT_FORMATS.get(mime_type)

        async with httpx.AsyncClient() as client:
            if export_mime:
                url = _DRIVE_EXPORT_URL.format(file_id=request.file_id)
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
            response.raise_for_status()
            file_data = response.content

        storage_key = f"{user_id}/{request.workspace_id}/{uuid4()}/{request.filename}"
        await self._storage_client.upload_object(
            bucket="chat-attachments",
            key=storage_key,
            data=file_data,
            content_type=mime_type,
        )

        expires_at = datetime.now(UTC) + timedelta(hours=24)
        attachment = ChatAttachment(
            id=uuid4(),
            user_id=user_id,
            workspace_id=request.workspace_id,
            session_id=request.session_id,
            filename=request.filename,
            mime_type=mime_type,
            size_bytes=len(file_data),
            source="google_drive",
            storage_key=storage_key,
            expires_at=expires_at,
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
