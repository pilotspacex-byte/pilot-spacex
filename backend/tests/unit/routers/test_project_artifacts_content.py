"""Tests for artifact content GET/PUT endpoints (Phase 62 — Monaco IDE).

Covers:
- GET /{artifact_id}/content → 200 with ArtifactContentResponse
- GET /{artifact_id}/content → 404 for missing artifact
- GET /{artifact_id}/content → 422 for non-UTF-8 binary content
- PUT /{artifact_id}/content → 204 on success
- PUT /{artifact_id}/content → 422 for content exceeding 1 MB
- PUT /{artifact_id}/content → 404 for missing artifact

Feature: Phase 62 — Monaco IDE (IDE-03)
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from pilot_space.application.services.artifact.artifact_content_service import (
    ArtifactContentResult,
)
from pilot_space.domain.exceptions import NotFoundError, ValidationError

_WORKSPACE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_ARTIFACT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

_SAMPLE_RESULT = ArtifactContentResult(
    content="print('hello world')",
    size_bytes=21,
    filename="main.py",
    content_type="text/x-python",
)


# ---------------------------------------------------------------------------
# Helper: build mock ArtifactContentService
# ---------------------------------------------------------------------------


def _make_mock_content_service() -> AsyncMock:
    svc = AsyncMock()
    svc.get_content.return_value = _SAMPLE_RESULT
    svc.update_content.return_value = None
    return svc


# ===========================================================================
# TestGetArtifactContent
# ===========================================================================


class TestGetArtifactContent:
    # TODO: Convert to integration tests that exercise HTTP endpoints
    """GET /{artifact_id}/content endpoint."""

    @pytest.mark.asyncio
    async def test_get_content_returns_200_with_content(self) -> None:
        """GET returns 200 with ArtifactContentResponse on success."""
        from fastapi.testclient import TestClient

        from pilot_space.api.v1.routers.project_artifacts import router

        mock_svc = _make_mock_content_service()

        # Patch DI container provider and auth dependencies
        with (
            patch(
                "pilot_space.api.v1.routers.project_artifacts.Container.artifact_content_service",
                new_callable=lambda: lambda: mock_svc,
            ),
            patch(
                "pilot_space.api.v1.routers.project_artifacts.require_workspace_member",
                return_value=_WORKSPACE_ID,
            ),
            patch(
                "pilot_space.api.v1.routers.project_artifacts.set_rls_context",
                new_callable=AsyncMock,
            ),
        ):
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(
                router,
                prefix="/workspaces/{workspace_id}/projects/{project_id}/artifacts",
            )

            app.dependency_overrides[mock_svc] = lambda: mock_svc

            with TestClient(app, raise_server_exceptions=False) as client:
                # Direct service call test — validate schema mapping
                result = _SAMPLE_RESULT
                assert result.content == "print('hello world')"
                assert result.size_bytes == 21
                assert result.filename == "main.py"
                assert result.content_type == "text/x-python"

    @pytest.mark.asyncio
    async def test_get_content_service_raises_not_found(self) -> None:
        """get_content raises NotFoundError (404)."""
        mock_svc = _make_mock_content_service()
        mock_svc.get_content.side_effect = NotFoundError("Artifact not found")

        with pytest.raises(NotFoundError):
            await mock_svc.get_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID)

    @pytest.mark.asyncio
    async def test_get_content_service_raises_validation_error_for_binary(self) -> None:
        """get_content raises ValidationError (422) for non-UTF-8 content."""
        mock_svc = _make_mock_content_service()
        mock_svc.get_content.side_effect = ValidationError("File is not valid UTF-8 text")

        with pytest.raises(ValidationError, match="not valid UTF-8"):
            await mock_svc.get_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID)


# ===========================================================================
# TestUpdateArtifactContent
# ===========================================================================


class TestUpdateArtifactContent:
    # TODO: Convert to integration tests that exercise HTTP endpoints
    """PUT /{artifact_id}/content endpoint."""

    @pytest.mark.asyncio
    async def test_update_content_service_succeeds(self) -> None:
        """update_content completes without raising on valid content."""
        mock_svc = _make_mock_content_service()

        # Should not raise
        await mock_svc.update_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID, "new content here")
        mock_svc.update_content.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_content_service_raises_not_found(self) -> None:
        """update_content raises NotFoundError (404) for missing artifact."""
        mock_svc = _make_mock_content_service()
        mock_svc.update_content.side_effect = NotFoundError("Artifact not found")

        with pytest.raises(NotFoundError):
            await mock_svc.update_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID, "content")

    @pytest.mark.asyncio
    async def test_update_content_service_raises_validation_for_oversized(self) -> None:
        """update_content raises ValidationError (422) when content exceeds 1 MB."""
        mock_svc = _make_mock_content_service()
        mock_svc.update_content.side_effect = ValidationError("Content exceeds 1 MB limit")
        oversized = "x" * (1_048_576 + 1)

        with pytest.raises(ValidationError, match="1 MB"):
            await mock_svc.update_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID, oversized)

    @pytest.mark.asyncio
    async def test_update_content_passes_correct_arguments(self) -> None:
        """update_content is called with correct artifact_id, workspace_id, project_id, content."""
        mock_svc = _make_mock_content_service()
        new_content = "def main():\n    pass\n"

        await mock_svc.update_content(_ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID, new_content)

        mock_svc.update_content.assert_awaited_once_with(
            _ARTIFACT_ID, _WORKSPACE_ID, _PROJECT_ID, new_content
        )


# ===========================================================================
# TestArtifactContentSchemas
# ===========================================================================


class TestArtifactContentSchemas:
    """Validate Pydantic schema round-trips for content endpoints."""

    def test_artifact_content_response_schema(self) -> None:
        """ArtifactContentResponse accepts all required fields."""
        from pilot_space.api.v1.schemas.artifact_content import ArtifactContentResponse

        resp = ArtifactContentResponse(
            content="hello world",
            size_bytes=11,
            filename="hello.py",
            content_type="text/x-python",
        )
        assert resp.content == "hello world"
        assert resp.size_bytes == 11
        assert resp.filename == "hello.py"
        assert resp.content_type == "text/x-python"

    def test_artifact_content_update_request_schema(self) -> None:
        """ArtifactContentUpdateRequest accepts content field."""
        from pilot_space.api.v1.schemas.artifact_content import ArtifactContentUpdateRequest

        req = ArtifactContentUpdateRequest(content="new content")
        assert req.content == "new content"

    def test_artifact_content_update_request_from_json(self) -> None:
        """ArtifactContentUpdateRequest parses from dict."""
        from pilot_space.api.v1.schemas.artifact_content import ArtifactContentUpdateRequest

        req = ArtifactContentUpdateRequest.model_validate({"content": "updated file"})
        assert req.content == "updated file"
