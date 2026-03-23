"""ArtifactUploadService — DB-first file upload for note artifacts.

Implements the upload lifecycle:
    1. Validate extension against allowlist (raises UNSUPPORTED_FILE_TYPE)
    2. Validate file size: 0 bytes → EMPTY_FILE; > 10MB → FILE_TOO_LARGE
    3. (Optional) MIME cross-check for image extensions
    4. Create DB record with status=pending_upload (DB-first pattern)
    5. Upload bytes to Supabase Storage bucket 'note-artifacts'
    6. Update DB status to 'ready'

Storage key format: {workspace_id}/{project_id}/{artifact_id}/{filename}
Bucket: note-artifacts (NO bucket prefix in key — bucket passed separately)

Size limit: 10 * 1024 * 1024 bytes — single flat limit, no per-type differentiation.

Feature: v1.1 — Artifacts (ARTF-04, ARTF-05, ARTF-06)
"""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.models.artifact import Artifact
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.api.v1.schemas.artifacts import ArtifactResponse
    from pilot_space.infrastructure.database.repositories.artifact_repository import (
        ArtifactRepository,
    )
    from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

_BUCKET = "note-artifacts"
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB flat limit — single limit, no per-type differentiation

# Extension allowlist — exact set from CONTEXT.md; lowercase only
_ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        # Documentation / data
        ".md",
        ".csv",
        ".json",
        ".txt",
        ".xlsx",
        ".xls",
        ".docx",  # Word (Office Open XML)
        ".doc",  # Word (legacy 97-2003)
        ".pptx",  # PowerPoint (Office Open XML)
        ".ppt",  # PowerPoint (legacy 97-2003)
        # Web / frontend
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".html",
        ".css",
        ".scss",
        # Backend languages
        ".py",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        # Config / markup
        ".yaml",
        ".yml",
        ".toml",
        ".xml",
        ".sql",
        ".sh",
        # Images
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".bmp",
        ".ico",
    }
)

# Image extensions that require an image/* MIME type prefix (advisory cross-check)
_IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".bmp",
        ".ico",
    }
)


def _validate_file_type(filename: str, content_type: str) -> None:
    """Validate extension against allowlist and perform MIME cross-check.

    Args:
        filename: Original filename including extension.
        content_type: MIME type provided by the client.

    Raises:
        ValueError: UNSUPPORTED_FILE_TYPE if extension not in allowlist.
        ValueError: MIME_MISMATCH if an image extension has a non-image/* MIME type.
    """
    ext = pathlib.Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValidationError("UNSUPPORTED_FILE_TYPE")
    # MIME cross-check: image extensions must have image/ MIME type prefix
    if ext in _IMAGE_EXTENSIONS and not content_type.startswith("image/"):
        raise ValidationError("MIME_MISMATCH")


def _validate_file_size(file_data: bytes) -> None:
    """Validate file size against limits.

    Args:
        file_data: Raw bytes of the file.

    Raises:
        ValueError: EMPTY_FILE if file_data is empty.
        ValueError: FILE_TOO_LARGE if file_data exceeds 10 MB.
    """
    if len(file_data) == 0:
        raise ValidationError("EMPTY_FILE")
    if len(file_data) > _MAX_BYTES:
        raise ValidationError("FILE_TOO_LARGE")


class ArtifactUploadService:
    """Service for uploading and deleting note artifacts.

    Validates file type and size, then follows the DB-first upload pattern:
    create DB record → upload to storage → mark as ready.

    If storage upload fails, the DB record remains in pending_upload status
    and will be cleaned up by the artifact_cleanup job after 24h.

    Example:
        service = ArtifactUploadService(session, storage_client, artifact_repo)
        response = await service.upload(
            file_data=file_bytes,
            filename="schema.sql",
            content_type="application/sql",
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=user_id,
        )
    """

    def __init__(
        self,
        session: AsyncSession,
        storage_client: SupabaseStorageClient,
        artifact_repo: ArtifactRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            storage_client: Supabase Storage client.
            artifact_repo: Artifact repository.
        """
        self._session = session
        self._storage = storage_client
        self._repo = artifact_repo

    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        workspace_id: UUID,
        project_id: UUID,
        user_id: UUID,
    ) -> ArtifactResponse:
        """Upload a file as a note artifact using the DB-first pattern.

        Validates extension allowlist and size before any I/O. Creates the DB
        record as pending_upload FIRST, then uploads to storage, then marks
        the record as ready.

        Args:
            file_data: Raw file bytes to upload.
            filename: Original filename including extension.
            content_type: MIME type of the file.
            workspace_id: Workspace owning the artifact.
            project_id: Project to associate the artifact with.
            user_id: User performing the upload.

        Returns:
            ArtifactResponse with artifact metadata.

        Raises:
            ValueError: UNSUPPORTED_FILE_TYPE if extension not in allowlist.
            ValueError: EMPTY_FILE if file_data is empty.
            ValueError: FILE_TOO_LARGE if size exceeds 10 MB.
            ValueError: MIME_MISMATCH if image extension has non-image MIME type.
        """
        # Validate first — no I/O until these pass
        _validate_file_type(filename, content_type)
        _validate_file_size(file_data)

        artifact_id = uuid4()
        # Sanitize filename: strip directory components to prevent path traversal
        safe_filename = pathlib.Path(filename).name
        # Storage key format: {workspace_id}/{project_id}/{artifact_id}/{filename}
        # IMPORTANT: NO bucket prefix — bucket passed separately to storage client
        storage_key = f"{workspace_id}/{project_id}/{artifact_id}/{safe_filename}"

        # Step 1 (DB-first): create record as pending_upload BEFORE storage upload
        artifact = Artifact(
            id=artifact_id,
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=user_id,
            filename=safe_filename,
            mime_type=content_type,
            size_bytes=len(file_data),
            storage_key=storage_key,
            status="pending_upload",
        )
        persisted = await self._repo.create(artifact)
        logger.info("artifact_db_record_created", artifact_id=str(artifact_id))

        # Step 2: upload to storage
        # If this fails, the DB record stays pending_upload for cleanup job to handle
        await self._storage.upload_object(
            bucket=_BUCKET,
            key=storage_key,
            data=file_data,
            content_type=content_type,
        )
        logger.info(
            "artifact_uploaded_to_storage",
            artifact_id=str(artifact_id),
            size_bytes=len(file_data),
        )

        # Step 3: mark ready ONLY after storage upload succeeds
        await self._repo.update_status(artifact_id, "ready")

        # Lazy import to avoid circular: api.v1.schemas → api.v1.__init__ → routers
        from pilot_space.api.v1.schemas.artifacts import ArtifactResponse

        return ArtifactResponse(
            id=artifact_id,
            project_id=project_id,
            user_id=user_id,
            filename=safe_filename,
            mime_type=content_type,
            size_bytes=len(file_data),
            status="ready",
            created_at=persisted.created_at,
        )

    async def delete(
        self, artifact_id: UUID, user_id: UUID, workspace_id: UUID, project_id: UUID
    ) -> None:
        """Delete a note artifact.

        Verifies the artifact exists, belongs to the requesting workspace
        and project, and is owned by the requesting user before removing
        from storage and the database.

        Args:
            artifact_id: UUID of the artifact to delete.
            user_id: Authenticated user performing the deletion.
            workspace_id: Workspace scope for cross-tenant isolation.
            project_id: Project scope to prevent cross-project IDOR.

        Raises:
            ValueError: NOT_FOUND if artifact does not exist or belongs to
                a different workspace/project.
            ForbiddenError: FORBIDDEN if user does not own the artifact.
        """
        artifact = await self._repo.get_by_id(artifact_id)
        if artifact is None:
            raise NotFoundError("NOT_FOUND")
        # Cross-workspace/project isolation: treat mismatched artifacts as not found
        if artifact.workspace_id != workspace_id or artifact.project_id != project_id:
            raise NotFoundError("NOT_FOUND")
        if artifact.user_id != user_id:
            raise ForbiddenError("FORBIDDEN")

        await self._storage.delete_object(bucket=_BUCKET, key=artifact.storage_key)
        await self._repo.delete(artifact_id)
        logger.info("artifact_deleted", artifact_id=str(artifact_id))


__all__ = ["ArtifactUploadService"]
