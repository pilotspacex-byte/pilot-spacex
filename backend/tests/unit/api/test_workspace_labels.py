"""Unit tests for GET /workspaces/{workspace_id}/labels endpoint.

Tests the list_workspace_labels endpoint including membership checks,
label retrieval, and project filtering.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.api.v1.routers.workspaces import list_workspace_labels
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

pytestmark = pytest.mark.asyncio


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
        user_id = uuid4()
        member = _make_member(user_id)
        workspace = _make_workspace(workspace_id, members=[member])

        labels = [_make_label("bug", "#D9534F"), _make_label("feature", "#29A386")]

        workspace_repo = AsyncMock()
        workspace_repo.get_with_members.return_value = workspace
        workspace_repo.get_by_slug_with_members.return_value = workspace

        label_repo = AsyncMock()
        label_repo.get_workspace_labels.return_value = labels

        result = await list_workspace_labels(
            workspace_id=str(workspace_id),
            current_user_id=user_id,
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
        user_id = uuid4()
        workspace = _make_workspace(workspace_id, [_make_member(user_id)])

        workspace_repo = AsyncMock()
        workspace_repo.get_with_members.return_value = workspace
        workspace_repo.get_by_slug_with_members.return_value = workspace

        label_repo = AsyncMock()
        label_repo.get_workspace_labels.return_value = []

        result = await list_workspace_labels(
            workspace_id=str(workspace_id),
            current_user_id=user_id,
            workspace_repo=workspace_repo,
            label_repo=label_repo,
            project_id=None,
        )

        assert result == []

    async def test_passes_project_id_filter(self):
        """Project ID is forwarded to repository."""
        workspace_id = uuid4()
        project_id = uuid4()
        user_id = uuid4()
        workspace = _make_workspace(workspace_id, [_make_member(user_id)])

        workspace_repo = AsyncMock()
        workspace_repo.get_with_members.return_value = workspace
        workspace_repo.get_by_slug_with_members.return_value = workspace

        label_repo = AsyncMock()
        label_repo.get_workspace_labels.return_value = []

        await list_workspace_labels(
            workspace_id=str(workspace_id),
            current_user_id=user_id,
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
        user_id = uuid4()
        other_member = _make_member(uuid4())  # Different user
        workspace = _make_workspace(workspace_id, [other_member])

        workspace_repo = AsyncMock()
        workspace_repo.get_with_members.return_value = workspace
        workspace_repo.get_by_slug_with_members.return_value = workspace

        label_repo = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await list_workspace_labels(
                workspace_id=str(workspace_id),
                current_user_id=user_id,
                workspace_repo=workspace_repo,
                label_repo=label_repo,
                project_id=None,
            )

        assert exc_info.value.status_code == 403

    async def test_workspace_not_found(self):
        """Missing workspace returns 404."""
        from fastapi import HTTPException

        workspace_repo = AsyncMock()
        workspace_repo.get_with_members.return_value = None
        workspace_repo.get_by_slug_with_members.return_value = None

        label_repo = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await list_workspace_labels(
                workspace_id=str(uuid4()),
                current_user_id=uuid4(),
                workspace_repo=workspace_repo,
                label_repo=label_repo,
                project_id=None,
            )

        assert exc_info.value.status_code == 404

    async def test_demo_workspace_bypasses_membership_check(self, monkeypatch):
        """Demo workspace allows access without membership in dev mode."""
        monkeypatch.setenv("APP_ENV", "development")

        workspace_id = uuid4()
        non_member_user_id = uuid4()
        other_member = _make_member(uuid4())  # Different user
        workspace = _make_workspace(workspace_id, [other_member])

        labels = [_make_label("bug", "#D9534F")]

        workspace_repo = AsyncMock()
        workspace_repo.get_by_slug_with_members.return_value = workspace

        label_repo = AsyncMock()
        label_repo.get_workspace_labels.return_value = labels

        result = await list_workspace_labels(
            workspace_id="pilot-space-demo",
            current_user_id=non_member_user_id,
            workspace_repo=workspace_repo,
            label_repo=label_repo,
            project_id=None,
        )

        assert len(result) == 1
