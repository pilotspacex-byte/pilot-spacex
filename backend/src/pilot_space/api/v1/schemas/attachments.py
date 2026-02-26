"""Attachment API schemas.

Request and response schemas for chat context attachment endpoints.
Covers local file upload and Google Drive import flows.

Feature 020: Chat Context Attachments & Google Drive.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


class AttachmentUploadResponse(BaseSchema):
    """Response from POST /ai/attachments/upload and POST /ai/drive/import.

    Returned after a local file upload or a Google Drive import completes.
    The attachment record expires after a fixed TTL; callers must use
    `attachment_id` before `expires_at` passes.
    """

    attachment_id: UUID = Field(description="Unique identifier for the stored attachment")
    filename: str = Field(description="Original filename as supplied by the uploader")
    mime_type: str = Field(description="MIME type of the stored file")
    size_bytes: int = Field(ge=1, description="File size in bytes")
    source: Literal["local", "google_drive"] = Field(
        description="Origin of the attachment: direct upload or Google Drive import"
    )
    expires_at: datetime = Field(description="UTC timestamp after which the attachment is purged")


class DriveStatusResponse(BaseSchema):
    """Response from GET /ai/drive/status.

    Indicates whether the current user has an active Google Drive credential
    for the requested workspace.
    """

    connected: bool = Field(description="True if a valid Drive credential exists")
    google_email: str | None = Field(
        default=None,
        description="Google account email associated with the credential; null when not connected",
    )
    connected_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the credential was first stored; null when not connected",
    )


class DriveFileItem(BaseSchema):
    """A single file or folder entry returned by GET /ai/drive/files.

    Represents one item in a Google Drive directory listing.
    """

    id: str = Field(description="Google Drive file identifier")
    name: str = Field(description="Display name of the file or folder")
    mime_type: str = Field(description="MIME type reported by Google Drive")
    size_bytes: int | None = Field(
        default=None,
        description="File size in bytes; null for Google Workspace native formats and folders",
    )
    modified_at: datetime | None = Field(
        default=None,
        description="UTC timestamp of last modification in Drive; null if not provided by API",
    )
    is_folder: bool = Field(description="True when the item is a folder")
    icon_url: str | None = Field(
        default=None,
        description="URL to Google's icon image for this MIME type; null if unavailable",
    )


class DriveFileListResponse(BaseSchema):
    """Response from GET /ai/drive/files.

    Wraps a paginated list of Drive items. Pass `next_page_token` as the
    `page_token` query parameter in the next request to fetch more results.
    """

    files: list[DriveFileItem] = Field(description="Drive files and folders in the current page")
    next_page_token: str | None = Field(
        default=None,
        description="Opaque token for the next page; null when no further results exist",
    )


class DriveImportRequest(BaseSchema):
    """Request body for POST /ai/drive/import.

    Instructs the backend to download the specified Drive file and store it
    as a chat attachment. Google Workspace formats (Docs, Sheets, Slides)
    are exported as PDF before storage.
    """

    workspace_id: UUID = Field(description="Workspace the attachment belongs to")
    file_id: str = Field(description="Google Drive file identifier to import")
    filename: str = Field(
        min_length=1,
        max_length=255,
        description="Desired filename for the stored attachment (1–255 characters)",
    )
    mime_type: str = Field(
        description="MIME type of the Drive file; must be in the supported type whitelist"
    )
    session_id: str | None = Field(
        default=None,
        description="Chat session to associate the attachment with; null for session-less upload",
    )


__all__ = [
    "AttachmentUploadResponse",
    "DriveFileItem",
    "DriveFileListResponse",
    "DriveImportRequest",
    "DriveStatusResponse",
]
