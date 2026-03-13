"""Unit tests for workspace label listing via WorkspaceService.

Tests the list_labels service method including membership checks,
label retrieval, and project filtering.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.application.services.workspace import (
    ListLabelsPayload,
    WorkspaceService,
)
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
    ws.slug = "test-workspace"
    ws.members = members or []
    return ws


def _make_label(name="bug", color="#D9534F"):
    """Create a mock label."""
    label = MagicMock()
    label.id = uuid4()
    label.name = name
    label.color = color
    return label


def _make_service(workspace_repo, label_repo=None):
    """Create WorkspaceService with mocked repositories."""
    return WorkspaceService(
        workspace_repo=workspace_repo,
        user_repo=AsyncMock(),
        invitation_repo=AsyncMock(),
        label_repo=label_repo or AsyncMock(),
    )


class TestListWorkspaceLabels:
    """Tests for WorkspaceService.list_labels."""

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

        service = _make_service(workspace_repo, label_repo)

        result = await service.list_labels(
            ListLabelsPayload(
                workspace_id_or_slug=str(workspace_id),
                user_id=user_id,
                project_id=None,
            )
        )

        assert len(result.labels) == 2
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

        service = _make_service(workspace_repo, label_repo)

        result = await service.list_labels(
            ListLabelsPayload(
                workspace_id_or_slug=str(workspace_id),
                user_id=user_id,
                project_id=None,
            )
        )

        assert result.labels == []

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

        service = _make_service(workspace_repo, label_repo)

        await service.list_labels(
            ListLabelsPayload(
                workspace_id_or_slug=str(workspace_id),
                user_id=user_id,
                project_id=project_id,
            )
        )

        label_repo.get_workspace_labels.assert_called_once_with(
            workspace_id,
            include_project_labels=True,
            project_id=project_id,
        )

    async def test_rejects_non_member(self):
        """Non-members get ValueError."""
        workspace_id = uuid4()
        user_id = uuid4()
        other_member = _make_member(uuid4())  # Different user
        workspace = _make_workspace(workspace_id, [other_member])

        workspace_repo = AsyncMock()
        workspace_repo.get_with_members.return_value = workspace
        workspace_repo.get_by_slug_with_members.return_value = workspace

        service = _make_service(workspace_repo)

        with pytest.raises(ValueError, match=r"[Nn]ot a member"):
            await service.list_labels(
                ListLabelsPayload(
                    workspace_id_or_slug=str(workspace_id),
                    user_id=user_id,
                    project_id=None,
                )
            )

    async def test_workspace_not_found(self):
        """Missing workspace raises ValueError."""
        workspace_repo = AsyncMock()
        workspace_repo.get_with_members.return_value = None
        workspace_repo.get_by_slug_with_members.return_value = None

        service = _make_service(workspace_repo)

        with pytest.raises(ValueError, match=r"[Nn]ot found"):
            await service.list_labels(
                ListLabelsPayload(
                    workspace_id_or_slug=str(uuid4()),
                    user_id=uuid4(),
                    project_id=None,
                )
            )

    async def test_non_member_denied_access(self):
        """Non-member should get ValueError when accessing workspace labels."""
        workspace_id = uuid4()
        non_member_user_id = uuid4()
        other_member = _make_member(uuid4())  # Different user
        workspace = _make_workspace(workspace_id, [other_member])

        workspace_repo = AsyncMock()
        workspace_repo.get_with_members.return_value = workspace
        workspace_repo.get_by_slug_with_members.return_value = workspace

        service = _make_service(workspace_repo)

        with pytest.raises(ValueError, match=r"[Nn]ot a member|access denied|permission"):
            await service.list_labels(
                ListLabelsPayload(
                    workspace_id_or_slug=str(workspace_id),
                    user_id=non_member_user_id,
                    project_id=None,
                )
            )
