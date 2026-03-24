"""TDD tests for project_artifacts router — upload, list, signed URL, delete.

Tests call router functions directly with mocked dependencies (same pattern as
test_ai_attachments.py). No TestClient/HTTP stack used.

Tests are written FIRST (TDD red phase). They FAIL until the router at
``pilot_space.api.v1.routers.project_artifacts`` is implemented.

Covers:
- POST: valid file → 201 ArtifactResponse
- POST: file.size > 10MB (pre-read check) → 413
- POST: file_data > 10MB (post-read check, no Content-Length) → 413
- POST: service raises ValueError("UNSUPPORTED_FILE_TYPE") → 422 with allowed_extensions list
- POST: service raises ValueError("EMPTY_FILE") → 422
- GET list: returns 200 ArtifactListResponse
- GET signed URL: returns 200 ArtifactUrlResponse with url and expires_in
- DELETE: returns 204 (None)
- GET URL: artifact.workspace_id != path workspace_id → 404
- DELETE: service raises ForbiddenError("FORBIDDEN") → 403

Feature: v1.1 — Artifacts (ARTF-04, ARTF-05, ARTF-06)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, UploadFile

from pilot_space.api.v1.routers.project_artifacts import (
    delete_artifact,
    get_artifact_url,
    list_artifacts,
    upload_artifact,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _mock_rls():
    """Mock set_rls_context globally — unit tests use SQLite (no RLS support)."""
    with patch(
        "pilot_space.api.v1.routers.project_artifacts.set_rls_context",
        new_callable=AsyncMock,
    ):
        yield


# ---------------------------------------------------------------------------
# Fixed test IDs
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")
TEST_PROJECT_ID = UUID("cccccccc-0000-0000-0000-000000000003")
TEST_ARTIFACT_ID = UUID("dddddddd-0000-0000-0000-000000000004")
OTHER_WORKSPACE_ID = UUID("eeeeeeee-0000-0000-0000-000000000005")

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_current_user(user_id: UUID = TEST_USER_ID) -> MagicMock:
    """Build a minimal mock TokenPayload matching CurrentUser type.

    CurrentUser resolves to TokenPayload which exposes .user_id (not .id).
    """
    user = MagicMock()
    user.user_id = user_id
    return user


def _make_upload_file(
    filename: str = "script.py",
    content_type: str = "text/x-python",
    content: bytes = b"print('hello world')",
    size: int | None = None,
) -> MagicMock:
    """Build a minimal UploadFile mock."""
    f = MagicMock(spec=UploadFile)
    f.filename = filename
    f.content_type = content_type
    f.read = AsyncMock(return_value=content)
    f.size = size if size is not None else len(content)
    return f


def _make_artifact_response(
    artifact_id: UUID = TEST_ARTIFACT_ID,
    project_id: UUID = TEST_PROJECT_ID,
    user_id: UUID = TEST_USER_ID,
    workspace_id: UUID = TEST_WORKSPACE_ID,
) -> MagicMock:
    """Build a mock ArtifactResponse (returned by service.upload)."""
    from pilot_space.api.v1.schemas.artifacts import ArtifactResponse

    return ArtifactResponse(
        id=artifact_id,
        project_id=project_id,
        user_id=user_id,
        filename="script.py",
        mime_type="text/x-python",
        size_bytes=20,
        status="ready",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_artifact_orm(
    artifact_id: UUID = TEST_ARTIFACT_ID,
    workspace_id: UUID = TEST_WORKSPACE_ID,
    project_id: UUID = TEST_PROJECT_ID,
    user_id: UUID = TEST_USER_ID,
) -> MagicMock:
    """Build a mock ORM Artifact (returned by repo.get_by_id / list_by_project)."""
    art = MagicMock()
    art.id = artifact_id
    art.workspace_id = workspace_id
    art.project_id = project_id
    art.user_id = user_id
    art.filename = "script.py"
    art.mime_type = "text/x-python"
    art.size_bytes = 20
    art.storage_key = f"{workspace_id}/{project_id}/{artifact_id}/script.py"
    art.status = "ready"
    art.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return art


def _make_session() -> AsyncMock:
    """Mock async SQLAlchemy session (satisfies SessionDep)."""
    return AsyncMock()


def _make_artifact_service(
    upload_return: object = None,
    upload_raises: Exception | None = None,
    delete_raises: Exception | None = None,
) -> AsyncMock:
    """Build a mock ArtifactUploadService."""
    svc = AsyncMock()
    if upload_raises is not None:
        svc.upload = AsyncMock(side_effect=upload_raises)
    else:
        svc.upload = AsyncMock(return_value=upload_return)
    if delete_raises is not None:
        svc.delete = AsyncMock(side_effect=delete_raises)
    else:
        svc.delete = AsyncMock(return_value=None)
    return svc


def _make_artifact_repo(
    get_return: object = None,
    list_return: list | None = None,
) -> AsyncMock:
    """Build a mock ArtifactRepository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=get_return)
    repo.list_by_project = AsyncMock(return_value=list_return or [])
    return repo


def _make_storage_client(signed_url: str = "https://example.com/signed") -> AsyncMock:
    """Build a mock SupabaseStorageClient."""
    client = AsyncMock()
    client.get_signed_url = AsyncMock(return_value=signed_url)
    return client


# ===========================================================================
# TestUploadEndpoint — POST ""
# ===========================================================================


class TestUploadEndpoint:
    """POST /workspaces/{ws}/projects/{proj}/artifacts"""

    async def test_upload_valid_file_returns_201(self) -> None:
        """Valid .py file → 201 with ArtifactResponse."""
        artifact_response = _make_artifact_response()
        svc = _make_artifact_service(upload_return=artifact_response)
        file = _make_upload_file()
        session = _make_session()
        current_user = _make_current_user()

        result = await upload_artifact(
            workspace_id=TEST_WORKSPACE_ID,
            project_id=TEST_PROJECT_ID,
            file=file,
            session=session,
            current_user=current_user,
            _member=TEST_USER_ID,
            artifact_service=svc,
        )

        assert result.id == TEST_ARTIFACT_ID
        assert result.filename == "script.py"
        assert result.status == "ready"
        svc.upload.assert_awaited_once()

    async def test_upload_too_large_pre_check_returns_413(self) -> None:
        """file.size > 10MB (pre-read Content-Length check) → 413 before calling service."""
        svc = _make_artifact_service()
        file = _make_upload_file(
            filename="huge.py",
            content=b"x" * 100,  # read() returns small content, but size reports large
            size=_MAX_BYTES + 1,  # size attribute is over limit
        )
        session = _make_session()
        current_user = _make_current_user()

        with pytest.raises(HTTPException) as exc_info:
            await upload_artifact(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                file=file,
                session=session,
                current_user=current_user,
                _member=TEST_USER_ID,
                artifact_service=svc,
            )

        assert exc_info.value.status_code == 413
        # Service must NOT be called when pre-read check triggers
        svc.upload.assert_not_awaited()

    async def test_upload_too_large_post_read_returns_413(self) -> None:
        """file_data len > 10MB after read (no Content-Length) → 413."""
        oversized_bytes = b"x" * (_MAX_BYTES + 1)
        svc = _make_artifact_service()
        # size=None simulates chunked transfer encoding (no Content-Length header)
        file = _make_upload_file(
            filename="huge.py",
            content=oversized_bytes,
            size=None,  # no pre-read size hint
        )
        # Override size attribute to None so the pre-check is skipped
        file.size = None

        session = _make_session()
        current_user = _make_current_user()

        with pytest.raises(HTTPException) as exc_info:
            await upload_artifact(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                file=file,
                session=session,
                current_user=current_user,
                _member=TEST_USER_ID,
                artifact_service=svc,
            )

        assert exc_info.value.status_code == 413
        svc.upload.assert_not_awaited()

    async def test_upload_disallowed_extension_raises_value_error(self) -> None:
        """service raises ValueError("UNSUPPORTED_FILE_TYPE") → propagates to global handler."""
        svc = _make_artifact_service(upload_raises=ValidationError("UNSUPPORTED_FILE_TYPE"))
        file = _make_upload_file(
            filename="malware.exe",
            content_type="application/octet-stream",
            content=b"MZ fake exe",
        )
        session = _make_session()
        current_user = _make_current_user()

        with pytest.raises(ValidationError, match="UNSUPPORTED_FILE_TYPE"):
            await upload_artifact(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                file=file,
                session=session,
                current_user=current_user,
                _member=TEST_USER_ID,
                artifact_service=svc,
            )

    async def test_upload_empty_file_raises_value_error(self) -> None:
        """service raises ValueError("EMPTY_FILE") → propagates to global handler."""
        svc = _make_artifact_service(upload_raises=ValidationError("EMPTY_FILE"))
        file = _make_upload_file(
            filename="empty.py",
            content=b"",
        )
        # Suppress pre-read size check (0 bytes is under limit)
        file.size = 0
        session = _make_session()
        current_user = _make_current_user()

        with pytest.raises(ValidationError, match="EMPTY_FILE"):
            await upload_artifact(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                file=file,
                session=session,
                current_user=current_user,
                _member=TEST_USER_ID,
                artifact_service=svc,
            )


# ===========================================================================
# TestListArtifacts — GET ""
# ===========================================================================


class TestListArtifacts:
    """GET /workspaces/{ws}/projects/{proj}/artifacts"""

    async def test_list_artifacts_returns_200(self) -> None:
        """Repo returns 2 artifacts → 200 with ArtifactListResponse (total=2)."""
        art1 = _make_artifact_response()
        art2 = _make_artifact_response(artifact_id=uuid4())
        repo = _make_artifact_repo(list_return=[art1, art2])
        session = _make_session()
        current_user = _make_current_user()

        result = await list_artifacts(
            workspace_id=TEST_WORKSPACE_ID,
            project_id=TEST_PROJECT_ID,
            session=session,
            current_user=current_user,
            _member=TEST_USER_ID,
            artifact_repo=repo,
        )

        assert result.total == 2
        assert len(result.artifacts) == 2
        repo.list_by_project.assert_awaited_once_with(TEST_WORKSPACE_ID, TEST_PROJECT_ID)

    async def test_list_artifacts_empty_project(self) -> None:
        """No artifacts for project → 200 with empty list and total=0."""
        repo = _make_artifact_repo(list_return=[])
        session = _make_session()
        current_user = _make_current_user()

        result = await list_artifacts(
            workspace_id=TEST_WORKSPACE_ID,
            project_id=TEST_PROJECT_ID,
            session=session,
            current_user=current_user,
            _member=TEST_USER_ID,
            artifact_repo=repo,
        )

        assert result.total == 0
        assert result.artifacts == []


# ===========================================================================
# TestGetArtifactUrl — GET "/{artifact_id}/url"
# ===========================================================================


class TestGetArtifactUrl:
    """GET /workspaces/{ws}/projects/{proj}/artifacts/{id}/url"""

    async def test_get_signed_url_returns_200(self) -> None:
        """Existing artifact → 200 with ArtifactUrlResponse containing url and expires_in."""
        art = _make_artifact_orm()
        repo = _make_artifact_repo(get_return=art)
        storage = _make_storage_client(signed_url="https://storage.example.com/signed/script.py")
        session = _make_session()
        current_user = _make_current_user()

        result = await get_artifact_url(
            workspace_id=TEST_WORKSPACE_ID,
            project_id=TEST_PROJECT_ID,
            artifact_id=TEST_ARTIFACT_ID,
            session=session,
            current_user=current_user,
            _member=TEST_USER_ID,
            artifact_repo=repo,
            storage_client=storage,
        )

        assert result.url == "https://storage.example.com/signed/script.py"
        assert result.expires_in == 3600

    async def test_workspace_isolation_returns_404(self) -> None:
        """artifact.workspace_id != path workspace_id → 404 (cross-workspace isolation)."""
        # Artifact belongs to WORKSPACE_ID but request is for OTHER_WORKSPACE_ID
        art = _make_artifact_orm(workspace_id=TEST_WORKSPACE_ID)
        repo = _make_artifact_repo(get_return=art)
        storage = _make_storage_client()
        session = _make_session()
        current_user = _make_current_user()

        with pytest.raises(NotFoundError) as exc_info:
            await get_artifact_url(
                workspace_id=OTHER_WORKSPACE_ID,  # different workspace
                project_id=TEST_PROJECT_ID,
                artifact_id=TEST_ARTIFACT_ID,
                session=session,
                current_user=current_user,
                _member=TEST_USER_ID,
                artifact_repo=repo,
                storage_client=storage,
            )

        assert exc_info.value.http_status == 404

    async def test_artifact_not_found_returns_404(self) -> None:
        """repo.get_by_id returns None → 404."""
        repo = _make_artifact_repo(get_return=None)
        storage = _make_storage_client()
        session = _make_session()
        current_user = _make_current_user()

        with pytest.raises(NotFoundError) as exc_info:
            await get_artifact_url(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                artifact_id=uuid4(),
                session=session,
                current_user=current_user,
                _member=TEST_USER_ID,
                artifact_repo=repo,
                storage_client=storage,
            )

        assert exc_info.value.http_status == 404


# ===========================================================================
# TestDeleteArtifact — DELETE "/{artifact_id}"
# ===========================================================================


class TestDeleteArtifact:
    """DELETE /workspaces/{ws}/projects/{proj}/artifacts/{id}"""

    async def test_delete_artifact_returns_204(self) -> None:
        """Valid delete → service.delete called, returns None (204 no content)."""
        svc = _make_artifact_service()
        session = _make_session()
        current_user = _make_current_user()

        result = await delete_artifact(
            workspace_id=TEST_WORKSPACE_ID,
            project_id=TEST_PROJECT_ID,
            artifact_id=TEST_ARTIFACT_ID,
            session=session,
            current_user=current_user,
            _member=TEST_USER_ID,
            artifact_service=svc,
        )

        assert result is None
        svc.delete.assert_awaited_once_with(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
            workspace_id=TEST_WORKSPACE_ID,
            project_id=TEST_PROJECT_ID,
        )

    async def test_delete_forbidden_raises_forbidden_error(self) -> None:
        """service raises ForbiddenError("FORBIDDEN") → propagates to global handler."""
        svc = _make_artifact_service(delete_raises=ForbiddenError("FORBIDDEN"))
        session = _make_session()
        current_user = _make_current_user()

        with pytest.raises(ForbiddenError):
            await delete_artifact(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                artifact_id=TEST_ARTIFACT_ID,
                session=session,
                current_user=current_user,
                _member=TEST_USER_ID,
                artifact_service=svc,
            )

    async def test_delete_not_found_raises_value_error(self) -> None:
        """service raises ValueError("NOT_FOUND") → propagates to global handler."""
        svc = _make_artifact_service(delete_raises=ValueError("NOT_FOUND"))
        session = _make_session()
        current_user = _make_current_user()

        with pytest.raises(ValueError, match="NOT_FOUND"):
            await delete_artifact(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                artifact_id=TEST_ARTIFACT_ID,
                session=session,
                current_user=current_user,
                _member=TEST_USER_ID,
                artifact_service=svc,
            )


__all__: list[str] = []
