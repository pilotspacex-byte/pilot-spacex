"""Unit tests for entity_resolver (T003).

Tests resolve_entity_id() for UUID passthrough, PROJ-NNN resolution,
project identifier resolution, error handling, and format validation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.ai.tools.entity_resolver import resolve_entity_id


@dataclass
class FakeToolContext:
    """Minimal ToolContext for testing."""

    db_session: Any
    workspace_id: str
    user_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def _make_ctx(workspace_id: str | None = None) -> FakeToolContext:
    return FakeToolContext(
        db_session=MagicMock(),
        workspace_id=workspace_id or str(uuid.uuid4()),
    )


class TestUUIDPassthrough:
    """UUID strings should pass through without DB query."""

    @pytest.mark.asyncio
    async def test_valid_uuid(self) -> None:
        test_uuid = uuid.uuid4()
        ctx = _make_ctx()
        resolved, error = await resolve_entity_id("issue", str(test_uuid), ctx)
        assert resolved == test_uuid
        assert error is None

    @pytest.mark.asyncio
    async def test_uppercase_uuid(self) -> None:
        test_uuid = uuid.uuid4()
        ctx = _make_ctx()
        resolved, error = await resolve_entity_id("project", str(test_uuid).upper(), ctx)
        assert resolved == test_uuid
        assert error is None


class TestIssueIdentifierResolution:
    """PROJ-NNN format should resolve via IssueRepository."""

    @pytest.mark.asyncio
    async def test_valid_identifier(self) -> None:
        expected_id = uuid.uuid4()
        mock_issue = MagicMock()
        mock_issue.id = expected_id

        ctx = _make_ctx()
        with patch(
            "pilot_space.infrastructure.database.repositories.issue_repository.IssueRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_identifier = AsyncMock(return_value=mock_issue)

            resolved, error = await resolve_entity_id("issue", "PILOT-123", ctx)

        assert resolved == expected_id
        assert error is None
        mock_repo.get_by_identifier.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        ctx = _make_ctx()
        with patch(
            "pilot_space.infrastructure.database.repositories.issue_repository.IssueRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_identifier = AsyncMock(return_value=None)

            resolved, error = await resolve_entity_id("issue", "FAKE-999", ctx)

        assert resolved is None
        assert error is not None
        assert "not found" in error.lower()

    @pytest.mark.asyncio
    async def test_lowercase_identifier_rejected(self) -> None:
        ctx = _make_ctx()
        resolved, error = await resolve_entity_id("issue", "pilot-42", ctx)

        assert resolved is None
        assert error is not None
        assert "must be uppercase" in error

    @pytest.mark.asyncio
    async def test_invalid_format(self) -> None:
        ctx = _make_ctx()
        resolved, error = await resolve_entity_id("issue", "not-an-id", ctx)
        assert resolved is None
        assert error is not None
        assert "invalid" in error.lower()


class TestProjectIdentifierResolution:
    """Project identifiers (2-10 uppercase letters) should resolve via ProjectRepository."""

    @pytest.mark.asyncio
    async def test_valid_identifier(self) -> None:
        expected_id = uuid.uuid4()
        mock_project = MagicMock()
        mock_project.id = expected_id

        ctx = _make_ctx()
        with patch(
            "pilot_space.infrastructure.database.repositories.project_repository.ProjectRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_identifier = AsyncMock(return_value=mock_project)

            resolved, error = await resolve_entity_id("project", "PILOT", ctx)

        assert resolved == expected_id
        assert error is None

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        ctx = _make_ctx()
        with patch(
            "pilot_space.infrastructure.database.repositories.project_repository.ProjectRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_identifier = AsyncMock(return_value=None)

            resolved, error = await resolve_entity_id("project", "NOPE", ctx)

        assert resolved is None
        assert "not found" in error.lower()

    @pytest.mark.asyncio
    async def test_invalid_format(self) -> None:
        ctx = _make_ctx()
        resolved, error = await resolve_entity_id("project", "a", ctx)
        assert resolved is None
        assert "invalid" in error.lower()


class TestNoteIdentifier:
    """Notes only support UUID identifiers."""

    @pytest.mark.asyncio
    async def test_uuid_works(self) -> None:
        test_uuid = uuid.uuid4()
        ctx = _make_ctx()
        resolved, error = await resolve_entity_id("note", str(test_uuid), ctx)
        assert resolved == test_uuid

    @pytest.mark.asyncio
    async def test_non_uuid_rejected(self) -> None:
        ctx = _make_ctx()
        resolved, error = await resolve_entity_id("note", "some-note-name", ctx)
        assert resolved is None
        assert "uuid" in error.lower()


class TestEdgeCases:
    """Edge cases for entity resolution."""

    @pytest.mark.asyncio
    async def test_empty_string(self) -> None:
        ctx = _make_ctx()
        resolved, error = await resolve_entity_id("issue", "", ctx)
        assert resolved is None
        assert "empty" in error.lower()

    @pytest.mark.asyncio
    async def test_whitespace_only(self) -> None:
        ctx = _make_ctx()
        resolved, error = await resolve_entity_id("issue", "   ", ctx)
        assert resolved is None
        assert "empty" in error.lower()

    @pytest.mark.asyncio
    async def test_unknown_entity_type(self) -> None:
        ctx = _make_ctx()
        resolved, error = await resolve_entity_id("widget", "abc", ctx)
        assert resolved is None
        assert "unknown" in error.lower()
