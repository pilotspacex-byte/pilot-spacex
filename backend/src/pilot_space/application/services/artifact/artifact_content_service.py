"""ArtifactContentService — read/write code file content for Monaco IDE.

Implements the content read/write lifecycle:
    GET: Fetch artifact record → download bytes from storage → decode as UTF-8
    PUT: Fetch artifact record → encode content to bytes → upload to storage → update size_bytes

Bucket: note-artifacts (same as ArtifactUploadService)
Text size limit: 1 MB (1_048_576 bytes) — code files beyond this are impractical to edit.

Both operations verify workspace_id and project_id to prevent cross-tenant IDOR.

Feature: Phase 62 — Monaco IDE (IDE-03)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.domain.exceptions import NotFoundError, ValidationError
from pilot_space.infrastructure.database.models.artifact import Artifact
from pilot_space.infrastructure.database.repositories.artifact_repository import (
    ArtifactRepository,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

_BUCKET = "note-artifacts"
_MAX_TEXT_BYTES = 1_048_576  # 1 MB limit for text files


@dataclass
class ArtifactContentResult:
    """Result returned by get_content containing file content and metadata."""

    content: str
    size_bytes: int
    filename: str
    content_type: str


class ArtifactContentService:
    """Service for reading and writing note artifact file content.

    Provides UTF-8 text read/write operations for code files stored in
    Supabase Storage. Used by the Monaco IDE frontend to load and save
    file content.

    Both ``get_content`` and ``update_content`` verify workspace and project
    ownership before performing any storage I/O.

    Example:
        service = ArtifactContentService(session, storage_client)
        content = await service.get_content(artifact_id, workspace_id, project_id)
        await service.update_content(artifact_id, workspace_id, project_id, new_text)
    """

    def __init__(
        self,
        session: AsyncSession,
        storage_client: SupabaseStorageClient,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session (request-scoped).
            storage_client: Supabase Storage client (singleton).
        """
        self._session = session
        self._storage = storage_client
        self._repo = ArtifactRepository(session)

    async def _get_verified_artifact(
        self,
        artifact_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
    ) -> Artifact:
        """Fetch artifact and verify workspace/project ownership.

        Args:
            artifact_id: UUID of the artifact.
            workspace_id: Expected workspace for cross-tenant isolation.
            project_id: Expected project for cross-project IDOR prevention.

        Returns:
            The verified Artifact ORM instance.

        Raises:
            NotFoundError: If artifact is missing or belongs to a different workspace/project.
        """
        artifact = await self._repo.get_by_id(artifact_id)
        if artifact is None:
            raise NotFoundError("Artifact not found")
        if artifact.workspace_id != workspace_id or artifact.project_id != project_id:
            raise NotFoundError("Artifact not found")
        return artifact

    async def get_content(
        self,
        artifact_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
    ) -> ArtifactContentResult:
        """Download and return the UTF-8 text content of an artifact with metadata.

        Fetches the artifact record, verifies workspace/project ownership,
        downloads bytes from storage, and decodes as UTF-8.

        Args:
            artifact_id: UUID of the artifact to read.
            workspace_id: Workspace scope for cross-tenant isolation.
            project_id: Project scope for cross-project IDOR prevention.

        Returns:
            ArtifactContentResult with decoded text and artifact metadata.

        Raises:
            NotFoundError: If artifact does not exist or belongs to a different workspace/project.
            ValidationError: If the file content cannot be decoded as UTF-8.
        """
        artifact = await self._get_verified_artifact(artifact_id, workspace_id, project_id)

        logger.info(
            "artifact_content_get",
            artifact_id=str(artifact_id),
            storage_key=artifact.storage_key,
        )

        data = await self._storage.download_object(bucket=_BUCKET, key=artifact.storage_key)

        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError("File is not valid UTF-8 text") from exc

        return ArtifactContentResult(
            content=content,
            size_bytes=len(data),
            filename=artifact.filename,
            content_type=artifact.mime_type,
        )

    async def update_content(
        self,
        artifact_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
        content: str,
    ) -> None:
        """Overwrite artifact file content in storage and update size_bytes.

        Encodes content to UTF-8 bytes, validates the 1 MB size limit,
        uploads to Supabase Storage (upsert semantics), and updates the
        artifact's size_bytes field in the database.

        Args:
            artifact_id: UUID of the artifact to update.
            workspace_id: Workspace scope for cross-tenant isolation.
            project_id: Project scope for cross-project IDOR prevention.
            content: New UTF-8 text content to store.

        Raises:
            NotFoundError: If artifact does not exist or belongs to a different workspace/project.
            ValidationError: If encoded content exceeds the 1 MB text file limit.
        """
        artifact = await self._get_verified_artifact(artifact_id, workspace_id, project_id)

        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_TEXT_BYTES:
            raise ValidationError("Content exceeds 1 MB limit")

        await self._storage.upload_object(
            bucket=_BUCKET,
            key=artifact.storage_key,
            data=encoded,
            content_type="text/plain",
        )

        artifact.size_bytes = len(encoded)
        await self._session.commit()

        logger.info(
            "artifact_content_updated",
            artifact_id=str(artifact_id),
            size_bytes=len(encoded),
        )


__all__ = ["ArtifactContentResult", "ArtifactContentService"]
