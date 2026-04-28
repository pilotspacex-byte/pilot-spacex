"""TDD tests for ArtifactUploadService nullable project_id support (Phase 87.1 Plan 01).

RED phase — these tests assert the new contract that emerges in Plan 87.1-01:

* ``ArtifactUploadService.upload`` accepts ``project_id: UUID | None``.
* When ``project_id`` is ``None`` the storage key uses the literal segment
  ``ai-generated`` between workspace_id and artifact_id.
* When ``project_id`` is a real UUID the existing key shape is preserved
  (regression guard).
* ``ArtifactResponse.project_id`` may be ``None``.
* Filename sanitisation still strips path-traversal segments.
* The 10MB ceiling still applies regardless of project_id.

These tests intentionally fail today because:
  (a) ``upload`` signature requires ``project_id: UUID`` (not Optional)
  (b) ``ArtifactResponse.project_id`` is non-nullable
  (c) the storage key has no ``ai-generated`` branch.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.application.services.artifact.artifact_upload_service import (
    ArtifactUploadService,
)
from pilot_space.domain.exceptions import ValidationError

_MAX_BYTES = 10 * 1024 * 1024

_WORKSPACE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_USER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

_AI_GEN_KEY_RE = re.compile(r"^[0-9a-f-]+/ai-generated/[0-9a-f-]+/[^/]+$")
_PROJECT_KEY_RE = re.compile(r"^[0-9a-f-]+/[0-9a-f-]+/[0-9a-f-]+/[^/]+$")


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_storage_client() -> AsyncMock:
    client = AsyncMock()
    client.upload_object.return_value = None
    client.delete_object.return_value = None
    return client


@pytest.fixture
def mock_artifact_repo() -> AsyncMock:
    return AsyncMock()


def _wire_repo_create(repo: AsyncMock, project_id: uuid.UUID | None) -> MagicMock:
    """Make ``repo.create`` return a lightweight mock artifact reflecting project_id."""
    art = MagicMock()
    art.id = uuid.uuid4()
    art.workspace_id = _WORKSPACE_ID
    art.project_id = project_id
    art.user_id = _USER_ID
    art.status = "pending_upload"
    art.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    repo.create.return_value = art
    return art


@pytest.fixture
def service(
    mock_session: AsyncMock,
    mock_storage_client: AsyncMock,
    mock_artifact_repo: AsyncMock,
) -> ArtifactUploadService:
    return ArtifactUploadService(
        session=mock_session,
        storage_client=mock_storage_client,
        artifact_repo=mock_artifact_repo,
    )


class TestNullableProjectId:
    """upload() with project_id=None must succeed and use 'ai-generated' segment."""

    @pytest.mark.asyncio
    async def test_upload_with_none_project_id_returns_response_with_none(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
    ) -> None:
        _wire_repo_create(mock_artifact_repo, None)

        response = await service.upload(
            file_data=b"# AI generated",
            filename="ai-output.md",
            content_type="text/markdown",
            workspace_id=_WORKSPACE_ID,
            project_id=None,
            user_id=_USER_ID,
        )

        assert response.project_id is None

    @pytest.mark.asyncio
    async def test_upload_with_none_project_id_storage_key_has_ai_generated_segment(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
    ) -> None:
        _wire_repo_create(mock_artifact_repo, None)

        await service.upload(
            file_data=b"<html></html>",
            filename="report.html",
            content_type="text/html",
            workspace_id=_WORKSPACE_ID,
            project_id=None,
            user_id=_USER_ID,
        )

        mock_storage_client.upload_object.assert_awaited_once()
        key = mock_storage_client.upload_object.call_args.kwargs["key"]
        assert _AI_GEN_KEY_RE.match(key), (
            f"Expected key to match {_AI_GEN_KEY_RE.pattern}, got: {key}"
        )
        assert "/ai-generated/" in key

    @pytest.mark.asyncio
    async def test_upload_with_real_project_id_preserves_existing_key_shape(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
    ) -> None:
        _wire_repo_create(mock_artifact_repo, _PROJECT_ID)

        await service.upload(
            file_data=b"print('hi')",
            filename="script.py",
            content_type="text/x-python",
            workspace_id=_WORKSPACE_ID,
            project_id=_PROJECT_ID,
            user_id=_USER_ID,
        )

        mock_storage_client.upload_object.assert_awaited_once()
        key = mock_storage_client.upload_object.call_args.kwargs["key"]
        assert "/ai-generated/" not in key
        assert _PROJECT_KEY_RE.match(key), (
            f"Expected key to match {_PROJECT_KEY_RE.pattern}, got: {key}"
        )
        assert str(_PROJECT_ID) in key

    @pytest.mark.asyncio
    async def test_filename_sanitisation_with_none_project_id(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
    ) -> None:
        """Path-traversal segments must be stripped even when project_id is None."""
        _wire_repo_create(mock_artifact_repo, None)

        await service.upload(
            file_data=b"# md",
            filename="../../etc/passwd.md",
            content_type="text/markdown",
            workspace_id=_WORKSPACE_ID,
            project_id=None,
            user_id=_USER_ID,
        )

        key = mock_storage_client.upload_object.call_args.kwargs["key"]
        assert "../" not in key
        assert "/etc/" not in key
        # The sanitised segment is just the basename
        assert key.endswith("/passwd.md")

    @pytest.mark.asyncio
    async def test_oversized_payload_rejected_with_none_project_id(
        self,
        service: ArtifactUploadService,
    ) -> None:
        """The 10MB ceiling applies regardless of project_id."""
        oversized = b"x" * (_MAX_BYTES + 1)

        with pytest.raises(ValidationError, match="FILE_TOO_LARGE"):
            await service.upload(
                file_data=oversized,
                filename="huge.md",
                content_type="text/markdown",
                workspace_id=_WORKSPACE_ID,
                project_id=None,
                user_id=_USER_ID,
            )
