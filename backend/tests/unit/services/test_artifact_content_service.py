"""TDD tests for ArtifactContentService — read/write file content for Monaco IDE.

Tests written FIRST (TDD red phase). The service at
``pilot_space.application.services.artifact.artifact_content_service``
does NOT exist yet; every test is expected to FAIL until the implementation
is provided.

Covers:
- get_content: returns UTF-8 string for valid artifact
- get_content: raises NotFoundError for missing artifact
- get_content: raises NotFoundError for wrong workspace/project
- get_content: raises ValidationError for non-UTF-8 binary content
- update_content: calls storage.upload_object and updates size_bytes
- update_content: raises NotFoundError for missing artifact
- update_content: raises ValidationError when content exceeds 1 MB
- download_object: returns bytes from storage bucket

Feature: Phase 62 — Monaco IDE (IDE-03)
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.application.services.artifact.artifact_content_service import (
    _BUCKET,
    _MAX_TEXT_BYTES,
)
from pilot_space.domain.exceptions import NotFoundError, ValidationError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WORKSPACE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_ARTIFACT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
_OTHER_WORKSPACE_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
_OTHER_PROJECT_ID = uuid.UUID("88888888-8888-8888-8888-888888888888")
_STORAGE_KEY = f"{_WORKSPACE_ID}/{_PROJECT_ID}/{_ARTIFACT_ID}/main.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_artifact(
    workspace_id: uuid.UUID = _WORKSPACE_ID,
    project_id: uuid.UUID = _PROJECT_ID,
) -> MagicMock:
    """Build a mock ORM Artifact record."""
    art = MagicMock()
    art.id = _ARTIFACT_ID
    art.workspace_id = workspace_id
    art.project_id = project_id
    art.storage_key = _STORAGE_KEY
    art.filename = "main.py"
    art.mime_type = "text/x-python"
    art.size_bytes = 42
    return art


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock async SQLAlchemy session."""
    return AsyncMock()


@pytest.fixture
def mock_storage_client() -> AsyncMock:
    """Mock SupabaseStorageClient with download_object and upload_object."""
    client = AsyncMock()
    client.download_object.return_value = b"print('hello')"
    client.upload_object.return_value = _STORAGE_KEY
    return client


@pytest.fixture
def mock_artifact_repo() -> AsyncMock:
    """Mock ArtifactRepository."""
    return AsyncMock()


@pytest.fixture
def service(
    mock_session: AsyncMock,
    mock_storage_client: AsyncMock,
    mock_artifact_repo: AsyncMock,
) -> object:
    """Create ArtifactContentService with all dependencies mocked."""
    from pilot_space.application.services.artifact.artifact_content_service import (
        ArtifactContentService,
    )

    # Patch the ArtifactRepository constructor to return our mock repo
    with patch(
        "pilot_space.application.services.artifact.artifact_content_service.ArtifactRepository",
        return_value=mock_artifact_repo,
    ):
        return ArtifactContentService(
            session=mock_session,
            storage_client=mock_storage_client,
        )


# ===========================================================================
# TestDownloadObject
# ===========================================================================


class TestDownloadObject:
    """SupabaseStorageClient.download_object returns bytes from storage."""

    @pytest.mark.asyncio
    async def test_download_object_returns_bytes(self) -> None:
        """download_object returns bytes on success."""
        from unittest.mock import MagicMock

        from pilot_space.infrastructure.storage.client import SupabaseStorageClient

        client = SupabaseStorageClient()
        # Use MagicMock for synchronous storage chain, AsyncMock only for download
        mock_bucket = MagicMock()
        mock_bucket.download = AsyncMock(return_value=b"file content")
        mock_storage = MagicMock()
        mock_storage.from_.return_value = mock_bucket
        mock_supabase = MagicMock()
        mock_supabase.storage = mock_storage
        client._client = mock_supabase  # type: ignore[assignment]

        result = await client.download_object(bucket=_BUCKET, key="ws/proj/file.py")

        assert result == b"file content"
        mock_storage.from_.assert_called_once_with("note-artifacts")
        mock_bucket.download.assert_awaited_once_with("ws/proj/file.py")

    @pytest.mark.asyncio
    async def test_download_object_raises_storage_download_error_on_failure(self) -> None:
        """download_object wraps exceptions in StorageDownloadError."""
        from unittest.mock import MagicMock

        from pilot_space.infrastructure.storage.client import (
            StorageDownloadError,
            SupabaseStorageClient,
        )

        client = SupabaseStorageClient()
        mock_bucket = MagicMock()
        mock_bucket.download = AsyncMock(side_effect=Exception("network error"))
        mock_storage = MagicMock()
        mock_storage.from_.return_value = mock_bucket
        mock_supabase = MagicMock()
        mock_supabase.storage = mock_storage
        client._client = mock_supabase  # type: ignore[assignment]

        with pytest.raises(StorageDownloadError, match="Failed to download"):
            await client.download_object(bucket=_BUCKET, key="ws/proj/file.py")


# ===========================================================================
# TestGetContent
# ===========================================================================


class TestGetContent:
    """ArtifactContentService.get_content — read file content from storage."""

    @pytest.mark.asyncio
    async def test_get_content_returns_utf8_string(
        self,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
        service: object,
    ) -> None:
        """get_content returns decoded UTF-8 string for a valid artifact."""
        from pilot_space.application.services.artifact.artifact_content_service import (
            ArtifactContentService,
        )

        assert isinstance(service, ArtifactContentService)
        mock_artifact_repo.get_by_id.return_value = _make_artifact()
        mock_storage_client.download_object.return_value = b"print('hello world')"

        result = await service.get_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID)

        assert result.content == "print('hello world')"
        assert result.filename == "main.py"
        assert result.content_type == "text/x-python"
        mock_storage_client.download_object.assert_awaited_once_with(
            bucket=_BUCKET,
            key=_STORAGE_KEY,
        )

    @pytest.mark.asyncio
    async def test_get_content_raises_not_found_for_missing_artifact(
        self,
        mock_artifact_repo: AsyncMock,
        service: object,
    ) -> None:
        """get_content raises NotFoundError when artifact_id does not exist."""
        from pilot_space.application.services.artifact.artifact_content_service import (
            ArtifactContentService,
        )

        assert isinstance(service, ArtifactContentService)
        mock_artifact_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.get_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID)

    @pytest.mark.asyncio
    async def test_get_content_raises_not_found_for_wrong_workspace(
        self,
        mock_artifact_repo: AsyncMock,
        service: object,
    ) -> None:
        """get_content raises NotFoundError when artifact belongs to different workspace."""
        from pilot_space.application.services.artifact.artifact_content_service import (
            ArtifactContentService,
        )

        assert isinstance(service, ArtifactContentService)
        # Artifact is in _OTHER_WORKSPACE_ID but request is for _WORKSPACE_ID
        mock_artifact_repo.get_by_id.return_value = _make_artifact(workspace_id=_OTHER_WORKSPACE_ID)

        with pytest.raises(NotFoundError):
            await service.get_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID)

    @pytest.mark.asyncio
    async def test_get_content_raises_not_found_for_wrong_project(
        self,
        mock_artifact_repo: AsyncMock,
        service: object,
    ) -> None:
        """get_content raises NotFoundError when artifact belongs to different project."""
        from pilot_space.application.services.artifact.artifact_content_service import (
            ArtifactContentService,
        )

        assert isinstance(service, ArtifactContentService)
        mock_artifact_repo.get_by_id.return_value = _make_artifact(project_id=_OTHER_PROJECT_ID)

        with pytest.raises(NotFoundError):
            await service.get_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID)

    @pytest.mark.asyncio
    async def test_get_content_raises_validation_error_for_non_utf8(
        self,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
        service: object,
    ) -> None:
        """get_content raises ValidationError when file content is not valid UTF-8."""
        from pilot_space.application.services.artifact.artifact_content_service import (
            ArtifactContentService,
        )

        assert isinstance(service, ArtifactContentService)
        mock_artifact_repo.get_by_id.return_value = _make_artifact()
        # Invalid UTF-8 bytes (lone continuation byte)
        mock_storage_client.download_object.return_value = b"\xff\xfe binary\x00data"

        with pytest.raises(ValidationError, match="not valid UTF-8"):
            await service.get_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID)


# ===========================================================================
# TestUpdateContent
# ===========================================================================


class TestUpdateContent:
    """ArtifactContentService.update_content — write file content to storage."""

    @pytest.mark.asyncio
    async def test_update_content_calls_upload_and_updates_size(
        self,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
        mock_session: AsyncMock,
        service: object,
    ) -> None:
        """update_content writes bytes to storage and updates artifact.size_bytes."""
        from pilot_space.application.services.artifact.artifact_content_service import (
            ArtifactContentService,
        )

        assert isinstance(service, ArtifactContentService)
        artifact = _make_artifact()
        mock_artifact_repo.get_by_id.return_value = artifact
        new_content = "def hello():\n    print('updated')\n"

        await service.update_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID, new_content)

        encoded = new_content.encode("utf-8")
        mock_storage_client.upload_object.assert_awaited_once_with(
            bucket=_BUCKET,
            key=_STORAGE_KEY,
            data=encoded,
            content_type="text/plain",
        )
        assert artifact.size_bytes == len(encoded)
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_content_raises_not_found_for_missing_artifact(
        self,
        mock_artifact_repo: AsyncMock,
        service: object,
    ) -> None:
        """update_content raises NotFoundError for missing artifact."""
        from pilot_space.application.services.artifact.artifact_content_service import (
            ArtifactContentService,
        )

        assert isinstance(service, ArtifactContentService)
        mock_artifact_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.update_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID, "content")

    @pytest.mark.asyncio
    async def test_update_content_raises_validation_error_for_oversized_content(
        self,
        mock_artifact_repo: AsyncMock,
        service: object,
    ) -> None:
        """update_content raises ValidationError when content exceeds 1 MB."""
        from pilot_space.application.services.artifact.artifact_content_service import (
            ArtifactContentService,
        )

        assert isinstance(service, ArtifactContentService)
        mock_artifact_repo.get_by_id.return_value = _make_artifact()
        oversized_content = "x" * (_MAX_TEXT_BYTES + 1)

        with pytest.raises(ValidationError, match="1 MB"):
            await service.update_content(
                _ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID, oversized_content
            )

    @pytest.mark.asyncio
    async def test_update_content_raises_not_found_for_wrong_workspace(
        self,
        mock_artifact_repo: AsyncMock,
        service: object,
    ) -> None:
        """update_content raises NotFoundError when artifact belongs to different workspace."""
        from pilot_space.application.services.artifact.artifact_content_service import (
            ArtifactContentService,
        )

        assert isinstance(service, ArtifactContentService)
        mock_artifact_repo.get_by_id.return_value = _make_artifact(workspace_id=_OTHER_WORKSPACE_ID)

        with pytest.raises(NotFoundError):
            await service.update_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID, "content")
