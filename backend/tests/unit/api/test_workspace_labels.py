"""Unit tests for GET /workspaces/{workspace_id}/labels endpoint.

Tests the list_workspace_labels endpoint including membership checks,
label retrieval, and project filtering.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.api.v1.routers.workspaces import list_workspace_labels
from pilot_space.infrastructure.auth import TokenPayload
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

pytestmark = pytest.mark.asyncio


def _make_token(user_id=None):
    """Create a mock TokenPayload."""
    uid = user_id or uuid4()
    return TokenPayload(
        sub=str(uid),
        email="test@example.com",
        role="authenticated",
        aud="authenticated",
        exp=9999999999,
        iat=1700000000,
        app_metadata={},
        user_metadata={},
    )


def _make_member(user_id, role=WorkspaceRole.MEMBER):
    """Create a mock workspace member."""
    m = MagicMock()
    m.user_id = user_id
    m.role = role
    return m


def _make_workspace(workspace_id, members=None):
    """Create a mock workspace."""
    ws = MagicMock()
    ws.id = workspace_id
    ws.members = members or []
    return ws


def _make_label(name="bug", color="#D9534F"):
    """Create a mock label."""
    label = MagicMock()
    label.id = uuid4()
    label.name = name
    label.color = color
    return label


class TestListWorkspaceLabels:
    """Tests for list_workspace_labels endpoint."""

    async def test_returns_labels_for_member(self):
        """Member can list workspace labels."""
        workspace_id = uuid4()
        user = _make_token()
        member = _make_member(user.user_id)
        workspace = _make_workspace(workspace_id, members=[member])

        labels = [_make_label("bug", "#D9534F"), _make_label("feature", "#29A386")]

        workspace_repo = AsyncMock()
        workspace_repo.get_by_id.return_value = workspace

        label_repo = AsyncMock()
        label_repo.get_workspace_labels.return_value = labels

        result = await list_workspace_labels(
            workspace_id=workspace_id,
            current_user=user,
            workspace_repo=workspace_repo,
            label_repo=label_repo,
            project_id=None,
        )

        assert len(result) == 2
        label_repo.get_workspace_labels.assert_called_once_with(
            workspace_id,
            include_project_labels=True,
            project_id=None,
        )

    async def test_returns_empty_list_when_no_labels(self):
        """Returns empty list when workspace has no labels."""
        workspace_id = uuid4()
        user = _make_token()
        workspace = _make_workspace(workspace_id, [_make_member(user.user_id)])

        workspace_repo = AsyncMock()
        workspace_repo.get_by_id.return_value = workspace

        label_repo = AsyncMock()
        label_repo.get_workspace_labels.return_value = []

        result = await list_workspace_labels(
            workspace_id=workspace_id,
            current_user=user,
            workspace_repo=workspace_repo,
            label_repo=label_repo,
            project_id=None,
        )

        assert result == []

    async def test_passes_project_id_filter(self):
        """Project ID is forwarded to repository."""
        workspace_id = uuid4()
        project_id = uuid4()
        user = _make_token()
        workspace = _make_workspace(workspace_id, [_make_member(user.user_id)])

        workspace_repo = AsyncMock()
        workspace_repo.get_by_id.return_value = workspace

        label_repo = AsyncMock()
        label_repo.get_workspace_labels.return_value = []

        await list_workspace_labels(
            workspace_id=workspace_id,
            current_user=user,
            workspace_repo=workspace_repo,
            label_repo=label_repo,
            project_id=project_id,
        )

        label_repo.get_workspace_labels.assert_called_once_with(
            workspace_id,
            include_project_labels=True,
            project_id=project_id,
        )

    async def test_rejects_non_member(self):
        """Non-members get 403."""
        from fastapi import HTTPException

        workspace_id = uuid4()
        user = _make_token()
        other_member = _make_member(uuid4())  # Different user
        workspace = _make_workspace(workspace_id, [other_member])

        workspace_repo = AsyncMock()
        workspace_repo.get_by_id.return_value = workspace

        label_repo = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await list_workspace_labels(
                workspace_id=workspace_id,
                current_user=user,
                workspace_repo=workspace_repo,
                label_repo=label_repo,
                project_id=None,
            )

        assert exc_info.value.status_code == 403

    async def test_workspace_not_found(self):
        """Missing workspace returns 404."""
        from fastapi import HTTPException

        workspace_repo = AsyncMock()
        workspace_repo.get_by_id.return_value = None

        label_repo = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await list_workspace_labels(
                workspace_id=uuid4(),
                current_user=_make_token(),
                workspace_repo=workspace_repo,
                label_repo=label_repo,
                project_id=None,
            )

        assert exc_info.value.status_code == 404
