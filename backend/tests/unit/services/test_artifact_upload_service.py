"""TDD tests for ArtifactUploadService — DB-first upload flow for note artifacts.

Tests written FIRST (TDD red phase). The service at
``pilot_space.application.services.artifact.artifact_upload_service``
does NOT exist yet; every test is expected to FAIL until the implementation
is provided.

Covers:
- Upload validation: extension allowlist, 10MB flat size limit, empty file guard.
- MIME mismatch guard (optional cross-check for image extensions).
- Upload happy path: DB-first flow — repo.create before storage.upload_object,
  then repo.update_status("ready") after storage succeeds.
- Storage failure: repo.update_status NOT called when storage raises.
- Delete: storage.delete_object + repo.delete called on success.
- Delete error paths: NOT_FOUND when record absent, FORBIDDEN when wrong owner.

Feature: v1.1 — Artifacts (ARTF-04, ARTF-05, ARTF-06)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.application.services.artifact.artifact_upload_service import (
    ArtifactUploadService,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB flat limit

_WORKSPACE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_USER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
_OTHER_USER_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")

_SMALL_PY = b"print('hello world')"  # well under 10 MB
_SMALL_PNG = b"\x89PNG\r\n\x1a\n fake png content"  # well under 10 MB


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock async SQLAlchemy session."""
    return AsyncMock()


@pytest.fixture
def mock_storage_client() -> AsyncMock:
    """Mock SupabaseStorageClient."""
    client = AsyncMock()
    client.upload_object.return_value = "signed-url-placeholder"
    client.delete_object.return_value = None
    return client


@pytest.fixture
def mock_artifact_repo() -> AsyncMock:
    """Mock ArtifactRepository."""
    return AsyncMock()


@pytest.fixture
def mock_artifact() -> MagicMock:
    """A fake ORM Artifact record returned by repo.get_by_id."""
    art = MagicMock()
    art.id = uuid.uuid4()
    art.workspace_id = _WORKSPACE_ID
    art.project_id = _PROJECT_ID
    art.user_id = _USER_ID
    art.storage_key = f"{_WORKSPACE_ID}/{_PROJECT_ID}/{art.id}/test.py"
    art.status = "pending_upload"
    art.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return art


@pytest.fixture
def service(
    mock_session: AsyncMock,
    mock_storage_client: AsyncMock,
    mock_artifact_repo: AsyncMock,
) -> ArtifactUploadService:
    """Create ArtifactUploadService with all dependencies mocked."""
    return ArtifactUploadService(
        session=mock_session,
        storage_client=mock_storage_client,
        artifact_repo=mock_artifact_repo,
    )


# ---------------------------------------------------------------------------
# Helper: wire repo.create to return a mock artifact
# ---------------------------------------------------------------------------


def _wire_repo_create(mock_artifact_repo: AsyncMock, mock_artifact: MagicMock) -> None:
    """Make repo.create return mock_artifact (simulates DB flush+refresh)."""
    mock_artifact_repo.create.return_value = mock_artifact


# ===========================================================================
# TestExtensionAllowlist
# ===========================================================================


class TestExtensionAllowlist:
    """Extension allowlist enforcement — no I/O should occur before rejection."""

    @pytest.mark.asyncio
    async def test_allowed_extension_accepted(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """.py extension is in the allowlist — upload proceeds without ValueError."""
        _wire_repo_create(mock_artifact_repo, mock_artifact)

        # Should not raise
        await service.upload(
            file_data=_SMALL_PY,
            filename="script.py",
            content_type="text/x-python",
            workspace_id=_WORKSPACE_ID,
            project_id=_PROJECT_ID,
            user_id=_USER_ID,
        )

    @pytest.mark.asyncio
    async def test_blocked_extension_rejected(
        self,
        service: ArtifactUploadService,
    ) -> None:
        """.exe extension is NOT in the allowlist — raises ValueError('UNSUPPORTED_FILE_TYPE')."""
        with pytest.raises(ValidationError, match="UNSUPPORTED_FILE_TYPE"):
            await service.upload(
                file_data=b"\x7fELF malware bytes",
                filename="malware.exe",
                content_type="application/octet-stream",
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                user_id=_USER_ID,
            )

    @pytest.mark.asyncio
    async def test_pdf_extension_rejected(
        self,
        service: ArtifactUploadService,
    ) -> None:
        """.pdf is NOT in the extension allowlist (artifacts use code/image types only)."""
        with pytest.raises(ValidationError, match="UNSUPPORTED_FILE_TYPE"):
            await service.upload(
                file_data=b"%PDF-1.4 content",
                filename="document.pdf",
                content_type="application/pdf",
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                user_id=_USER_ID,
            )

    @pytest.mark.asyncio
    async def test_zip_extension_rejected(
        self,
        service: ArtifactUploadService,
    ) -> None:
        """.zip is NOT in the extension allowlist."""
        with pytest.raises(ValidationError, match="UNSUPPORTED_FILE_TYPE"):
            await service.upload(
                file_data=b"PK archive bytes",
                filename="archive.zip",
                content_type="application/zip",
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                user_id=_USER_ID,
            )

    @pytest.mark.asyncio
    async def test_png_extension_accepted(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """.png is in the allowlist — upload proceeds."""
        _wire_repo_create(mock_artifact_repo, mock_artifact)

        await service.upload(
            file_data=_SMALL_PNG,
            filename="screenshot.png",
            content_type="image/png",
            workspace_id=_WORKSPACE_ID,
            project_id=_PROJECT_ID,
            user_id=_USER_ID,
        )

    @pytest.mark.asyncio
    async def test_md_extension_accepted(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """.md is in the allowlist — upload proceeds."""
        _wire_repo_create(mock_artifact_repo, mock_artifact)

        await service.upload(
            file_data=b"# Markdown content",
            filename="README.md",
            content_type="text/markdown",
            workspace_id=_WORKSPACE_ID,
            project_id=_PROJECT_ID,
            user_id=_USER_ID,
        )

    @pytest.mark.asyncio
    async def test_ts_extension_accepted(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """.ts is in the allowlist — upload proceeds."""
        _wire_repo_create(mock_artifact_repo, mock_artifact)

        await service.upload(
            file_data=b"const x: string = 'hello';",
            filename="types.ts",
            content_type="text/typescript",
            workspace_id=_WORKSPACE_ID,
            project_id=_PROJECT_ID,
            user_id=_USER_ID,
        )


# ===========================================================================
# TestFileSizeValidation
# ===========================================================================


class TestFileSizeValidation:
    """Size limit: 10MB flat limit; empty file guard."""

    @pytest.mark.asyncio
    async def test_empty_file_rejected(
        self,
        service: ArtifactUploadService,
    ) -> None:
        """Zero-byte file raises ValueError('EMPTY_FILE')."""
        with pytest.raises(ValidationError, match="EMPTY_FILE"):
            await service.upload(
                file_data=b"",
                filename="empty.py",
                content_type="text/x-python",
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                user_id=_USER_ID,
            )

    @pytest.mark.asyncio
    async def test_file_too_large_rejected(
        self,
        service: ArtifactUploadService,
    ) -> None:
        """10_485_761 bytes raises ValueError('FILE_TOO_LARGE')."""
        oversized = b"x" * (_MAX_BYTES + 1)

        with pytest.raises(ValidationError, match="FILE_TOO_LARGE"):
            await service.upload(
                file_data=oversized,
                filename="big.py",
                content_type="text/x-python",
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                user_id=_USER_ID,
            )

    @pytest.mark.asyncio
    async def test_boundary_size_accepted(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """Exactly 10_485_760 bytes does NOT raise FILE_TOO_LARGE."""
        _wire_repo_create(mock_artifact_repo, mock_artifact)
        at_limit = b"x" * _MAX_BYTES

        # Should not raise FILE_TOO_LARGE
        await service.upload(
            file_data=at_limit,
            filename="maxsize.py",
            content_type="text/x-python",
            workspace_id=_WORKSPACE_ID,
            project_id=_PROJECT_ID,
            user_id=_USER_ID,
        )


# ===========================================================================
# TestMimeMismatch
# ===========================================================================


class TestMimeMismatch:
    """MIME cross-check: image extensions must have image/ content_type."""

    @pytest.mark.asyncio
    async def test_mime_mismatch_rejected(
        self,
        service: ArtifactUploadService,
    ) -> None:
        """Image extension with non-image MIME type raises ValueError('MIME_MISMATCH').

        filename='photo.png' has an image extension but content_type='application/json'
        is not an image/ MIME type — this triggers the MIME cross-check.
        """
        with pytest.raises(ValidationError, match="MIME_MISMATCH"):
            await service.upload(
                file_data=b"\x89PNG fake png",
                filename="photo.png",  # image extension — requires image/ MIME prefix
                content_type="application/json",  # wrong MIME category
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                user_id=_USER_ID,
            )

    @pytest.mark.asyncio
    async def test_image_with_wrong_category_mime_rejected(
        self,
        service: ArtifactUploadService,
    ) -> None:
        """filename='diagram.svg', content_type='application/json' → raises ValueError('MIME_MISMATCH')."""
        with pytest.raises(ValidationError, match="MIME_MISMATCH"):
            await service.upload(
                file_data=b"<svg>content</svg>",
                filename="diagram.svg",  # image/ prefix expected
                content_type="application/json",  # wrong category
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                user_id=_USER_ID,
            )


# ===========================================================================
# TestUploadHappyPath
# ===========================================================================


class TestUploadHappyPath:
    """DB-first upload flow: repo.create → storage.upload_object → repo.update_status."""

    @pytest.mark.asyncio
    async def test_upload_happy_path_db_first_ordering(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """DB record created BEFORE storage upload; status set to ready AFTER storage succeeds."""
        _wire_repo_create(mock_artifact_repo, mock_artifact)
        call_order: list[str] = []

        # Instrument to capture call order
        original_create = mock_artifact_repo.create.side_effect

        async def track_create(*args: Any, **kwargs: Any) -> MagicMock:
            call_order.append("repo.create")
            return mock_artifact

        async def track_upload(*args: Any, **kwargs: Any) -> str:
            call_order.append("storage.upload")
            return "url"

        async def track_update_status(*args: Any, **kwargs: Any) -> None:
            call_order.append("repo.update_status")

        mock_artifact_repo.create.side_effect = track_create
        mock_storage_client.upload_object.side_effect = track_upload
        mock_artifact_repo.update_status.side_effect = track_update_status

        await service.upload(
            file_data=_SMALL_PY,
            filename="script.py",
            content_type="text/x-python",
            workspace_id=_WORKSPACE_ID,
            project_id=_PROJECT_ID,
            user_id=_USER_ID,
        )

        # DB-first: create before upload, update_status after upload
        assert call_order == ["repo.create", "storage.upload", "repo.update_status"], (
            f"Expected DB-first order, got: {call_order}"
        )

    @pytest.mark.asyncio
    async def test_upload_calls_storage_with_correct_bucket(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """storage.upload_object called with bucket='note-artifacts'."""
        _wire_repo_create(mock_artifact_repo, mock_artifact)

        await service.upload(
            file_data=_SMALL_PY,
            filename="script.py",
            content_type="text/x-python",
            workspace_id=_WORKSPACE_ID,
            project_id=_PROJECT_ID,
            user_id=_USER_ID,
        )

        mock_storage_client.upload_object.assert_awaited_once()
        call_kwargs = mock_storage_client.upload_object.call_args
        # Check bucket argument
        bucket_arg = call_kwargs.kwargs.get("bucket") or call_kwargs.args[0]
        assert bucket_arg == "note-artifacts"

    @pytest.mark.asyncio
    async def test_upload_storage_key_format_no_bucket_prefix(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """Storage key must NOT include 'note-artifacts/' prefix — bucket passed separately."""
        _wire_repo_create(mock_artifact_repo, mock_artifact)

        await service.upload(
            file_data=_SMALL_PY,
            filename="script.py",
            content_type="text/x-python",
            workspace_id=_WORKSPACE_ID,
            project_id=_PROJECT_ID,
            user_id=_USER_ID,
        )

        mock_storage_client.upload_object.assert_awaited_once()
        call_kwargs = mock_storage_client.upload_object.call_args
        key_arg = call_kwargs.kwargs.get("key") or call_kwargs.args[1]

        # Key must NOT start with bucket name
        assert not key_arg.startswith("note-artifacts/"), (
            f"storage_key must not include bucket prefix. Got: {key_arg}"
        )
        # Key must contain workspace_id and filename
        assert str(_WORKSPACE_ID) in key_arg
        assert "script.py" in key_arg

    @pytest.mark.asyncio
    async def test_upload_update_status_called_with_ready(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """repo.update_status called with 'ready' after successful storage upload."""
        _wire_repo_create(mock_artifact_repo, mock_artifact)

        await service.upload(
            file_data=_SMALL_PY,
            filename="script.py",
            content_type="text/x-python",
            workspace_id=_WORKSPACE_ID,
            project_id=_PROJECT_ID,
            user_id=_USER_ID,
        )

        mock_artifact_repo.update_status.assert_awaited_once()
        # Second argument must be "ready"
        status_arg = mock_artifact_repo.update_status.call_args.args[1]
        assert status_arg == "ready"


# ===========================================================================
# TestStorageFailure
# ===========================================================================


class TestStorageFailure:
    """Storage upload failure: DB record stays pending_upload; update_status not called."""

    @pytest.mark.asyncio
    async def test_storage_failure_leaves_db_pending(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """When storage.upload_object raises, repo.update_status is NOT called."""
        _wire_repo_create(mock_artifact_repo, mock_artifact)
        mock_storage_client.upload_object.side_effect = Exception(
            "StorageUploadError: network failure"
        )

        with pytest.raises(Exception, match="StorageUploadError"):
            await service.upload(
                file_data=_SMALL_PY,
                filename="script.py",
                content_type="text/x-python",
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                user_id=_USER_ID,
            )

        # DB record must still be in pending_upload state (update_status not called)
        mock_artifact_repo.update_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_storage_failure_repo_create_was_called(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """Even on storage failure, repo.create was called (DB-first ensures cleanup job can find it)."""
        _wire_repo_create(mock_artifact_repo, mock_artifact)
        mock_storage_client.upload_object.side_effect = Exception(
            "StorageUploadError: network failure"
        )

        with pytest.raises(Exception, match="StorageUploadError"):
            await service.upload(
                file_data=_SMALL_PY,
                filename="script.py",
                content_type="text/x-python",
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                user_id=_USER_ID,
            )

        # Repo.create was called BEFORE storage (DB-first guarantees cleanup job finds stale record)
        mock_artifact_repo.create.assert_awaited_once()


# ===========================================================================
# TestDelete
# ===========================================================================


class TestDelete:
    """Delete orchestration: ownership check, storage delete, DB delete."""

    @pytest.mark.asyncio
    async def test_delete_removes_storage_and_db(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_storage_client: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """Valid delete: storage.delete_object called, then repo.delete called."""
        artifact_id = mock_artifact.id
        mock_artifact_repo.get_by_id.return_value = mock_artifact
        mock_artifact_repo.delete.return_value = True

        await service.delete(
            artifact_id=artifact_id,
            user_id=_USER_ID,
            workspace_id=_WORKSPACE_ID,
            project_id=_PROJECT_ID,
        )

        mock_storage_client.delete_object.assert_awaited_once_with(
            bucket="note-artifacts",
            key=mock_artifact.storage_key,
        )
        mock_artifact_repo.delete.assert_awaited_once_with(artifact_id)

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
    ) -> None:
        """repo.get_by_id returns None → raises ValueError('NOT_FOUND')."""
        mock_artifact_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError, match="NOT_FOUND"):
            await service.delete(
                artifact_id=uuid.uuid4(),
                user_id=_USER_ID,
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
            )

    @pytest.mark.asyncio
    async def test_delete_forbidden(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """artifact.user_id != requesting user_id → raises ForbiddenError('FORBIDDEN')."""
        mock_artifact_repo.get_by_id.return_value = mock_artifact

        with pytest.raises(ForbiddenError, match="FORBIDDEN"):
            await service.delete(
                artifact_id=mock_artifact.id,
                user_id=_OTHER_USER_ID,  # Different from mock_artifact.user_id = _USER_ID
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
            )

    @pytest.mark.asyncio
    async def test_delete_workspace_mismatch_treated_as_not_found(
        self,
        service: ArtifactUploadService,
        mock_artifact_repo: AsyncMock,
        mock_artifact: MagicMock,
    ) -> None:
        """Artifact from different workspace → raises ValueError('NOT_FOUND') (cross-workspace isolation)."""
        different_workspace = uuid.UUID("99999999-9999-9999-9999-999999999999")
        mock_artifact_repo.get_by_id.return_value = mock_artifact

        with pytest.raises(NotFoundError, match="NOT_FOUND"):
            await service.delete(
                artifact_id=mock_artifact.id,
                user_id=_USER_ID,
                workspace_id=different_workspace,  # artifact.workspace_id is _WORKSPACE_ID
                project_id=_PROJECT_ID,
            )
