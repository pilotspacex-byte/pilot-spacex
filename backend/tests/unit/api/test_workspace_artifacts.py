"""Unit tests for workspace_artifacts router (Phase 87.1 Plan 04 Rule 3 deviation).

Covers GET /workspaces/{ws}/artifacts/{id}/url — the workspace-scoped variant
that supports AI-generated artifacts where project_id IS NULL.

Pattern mirrors test_project_artifacts.TestGetArtifactUrl with no project_id.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.api.v1.routers.workspace_artifacts import get_workspace_artifact_url
from pilot_space.domain.exceptions import NotFoundError

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _mock_rls():
    with patch(
        "pilot_space.api.v1.routers.workspace_artifacts.set_rls_context",
        new_callable=AsyncMock,
    ):
        yield


TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")
TEST_ARTIFACT_ID = UUID("dddddddd-0000-0000-0000-000000000004")
OTHER_WORKSPACE_ID = UUID("eeeeeeee-0000-0000-0000-000000000005")


def _make_current_user(user_id: UUID = TEST_USER_ID) -> MagicMock:
    user = MagicMock()
    user.user_id = user_id
    return user


def _make_artifact_orm(
    artifact_id: UUID = TEST_ARTIFACT_ID,
    workspace_id: UUID = TEST_WORKSPACE_ID,
    project_id: UUID | None = None,  # AI-generated default: None
) -> MagicMock:
    art = MagicMock()
    art.id = artifact_id
    art.workspace_id = workspace_id
    art.project_id = project_id
    art.user_id = TEST_USER_ID
    art.filename = "report.md"
    art.mime_type = "text/markdown"
    art.size_bytes = 12
    seg = str(project_id) if project_id is not None else "ai-generated"
    art.storage_key = f"{workspace_id}/{seg}/{artifact_id}/report.md"
    art.status = "ready"
    art.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return art


def _make_session() -> AsyncMock:
    return AsyncMock()


def _make_artifact_repo(get_return: object = None) -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=get_return)
    return repo


def _make_storage_client(signed_url: str = "https://storage.example.com/signed") -> AsyncMock:
    client = AsyncMock()
    client.get_signed_url = AsyncMock(return_value=signed_url)
    return client


class TestGetWorkspaceArtifactUrl:
    """GET /workspaces/{workspace_id}/artifacts/{artifact_id}/url"""

    async def test_ai_generated_artifact_null_project_returns_signed_url(self) -> None:
        """project_id IS NULL → returns 200 with signed URL (the whole point of this endpoint)."""
        art = _make_artifact_orm(project_id=None)
        repo = _make_artifact_repo(get_return=art)
        storage = _make_storage_client(signed_url="https://storage.example.com/ai-generated/x.md")

        result = await get_workspace_artifact_url(
            workspace_id=TEST_WORKSPACE_ID,
            artifact_id=TEST_ARTIFACT_ID,
            session=_make_session(),
            current_user=_make_current_user(),
            _member=TEST_USER_ID,
            artifact_repo=repo,
            storage_client=storage,
        )

        assert result.url == "https://storage.example.com/ai-generated/x.md"
        assert result.expires_in == 3600
        storage.get_signed_url.assert_awaited_once()

    async def test_project_artifact_also_works(self) -> None:
        """project_id IS NOT NULL also flows through (no project_id filter on this route)."""
        art = _make_artifact_orm(project_id=uuid4())
        repo = _make_artifact_repo(get_return=art)
        storage = _make_storage_client()

        result = await get_workspace_artifact_url(
            workspace_id=TEST_WORKSPACE_ID,
            artifact_id=TEST_ARTIFACT_ID,
            session=_make_session(),
            current_user=_make_current_user(),
            _member=TEST_USER_ID,
            artifact_repo=repo,
            storage_client=storage,
        )

        assert result.expires_in == 3600

    async def test_cross_workspace_returns_404(self) -> None:
        """Artifact belongs to different workspace → NotFoundError (workspace isolation)."""
        art = _make_artifact_orm(workspace_id=TEST_WORKSPACE_ID)
        repo = _make_artifact_repo(get_return=art)
        storage = _make_storage_client()

        with pytest.raises(NotFoundError) as exc_info:
            await get_workspace_artifact_url(
                workspace_id=OTHER_WORKSPACE_ID,
                artifact_id=TEST_ARTIFACT_ID,
                session=_make_session(),
                current_user=_make_current_user(),
                _member=TEST_USER_ID,
                artifact_repo=repo,
                storage_client=storage,
            )

        assert exc_info.value.http_status == 404

    async def test_artifact_not_found_returns_404(self) -> None:
        """repo.get_by_id returns None → NotFoundError."""
        repo = _make_artifact_repo(get_return=None)
        storage = _make_storage_client()

        with pytest.raises(NotFoundError) as exc_info:
            await get_workspace_artifact_url(
                workspace_id=TEST_WORKSPACE_ID,
                artifact_id=uuid4(),
                session=_make_session(),
                current_user=_make_current_user(),
                _member=TEST_USER_ID,
                artifact_repo=repo,
                storage_client=storage,
            )

        assert exc_info.value.http_status == 404
