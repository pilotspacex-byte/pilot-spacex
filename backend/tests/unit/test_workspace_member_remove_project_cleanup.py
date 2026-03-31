"""Unit tests: workspace member removal cascades to project membership deactivation.

Bug fix: when a workspace member is removed, all their project_members rows
within that workspace must also be deactivated in the same transaction.

Source: 026-project-rbac bug report — "When you delete a user from the workspace,
it also removes all projects."
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pilot_space.application.services.workspace_member import (
    RemoveMemberPayload,
    WorkspaceMemberService,
)
from pilot_space.infrastructure.database.models.project_member import (
    ProjectMember,  # noqa: F401 — ensures SQLAlchemy mapper is configured before factories use it
)
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

from ..factories import UserFactory, WorkspaceFactory, WorkspaceMemberFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace_with_admin_and_member():
    """Create a workspace with an admin and a plain member."""
    admin = UserFactory(email="admin@example.com")
    member = UserFactory(email="member@example.com")
    workspace = WorkspaceFactory()
    admin_wm = WorkspaceMemberFactory(user=admin, workspace=workspace, role=WorkspaceRole.ADMIN)
    member_wm = WorkspaceMemberFactory(user=member, workspace=workspace, role=WorkspaceRole.MEMBER)
    workspace.members = [admin_wm, member_wm]
    return workspace, admin, member


def _make_service(workspace):
    """Build a WorkspaceMemberService with mocked repos."""
    mock_workspace_repo = AsyncMock()
    mock_workspace_repo.get_with_members.return_value = workspace
    mock_workspace_repo.remove_member.return_value = True
    mock_audit_repo = AsyncMock()
    svc = WorkspaceMemberService(
        workspace_repo=mock_workspace_repo,
        audit_log_repository=mock_audit_repo,
    )
    return svc, mock_workspace_repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRemoveMemberDeactivatesProjectMemberships:
    """Removing a workspace member must cascade-deactivate project memberships."""

    @pytest.mark.asyncio
    async def test_deactivate_all_for_user_in_workspace_called_with_correct_args(self) -> None:
        """remove_member calls deactivate_all_for_user_in_workspace with correct args."""
        workspace, admin, member = _make_workspace_with_admin_and_member()
        svc, _ = _make_service(workspace)
        mock_session = AsyncMock()

        with patch(
            "pilot_space.infrastructure.database.repositories.project_member.ProjectMemberRepository.deactivate_all_for_user_in_workspace",
            new_callable=AsyncMock,
            return_value=3,
        ) as mock_deactivate:
            result = await svc.remove_member(
                RemoveMemberPayload(
                    workspace_id=workspace.id,
                    target_user_id=member.id,
                    actor_id=admin.id,
                ),
                session=mock_session,
            )

        mock_deactivate.assert_awaited_once_with(
            user_id=member.id,
            workspace_id=workspace.id,
        )
        assert result.project_memberships_deactivated == 3

    @pytest.mark.asyncio
    async def test_result_has_zero_deactivated_when_no_project_memberships(self) -> None:
        """project_memberships_deactivated is 0 when user has no project assignments."""
        workspace, admin, member = _make_workspace_with_admin_and_member()
        svc, _ = _make_service(workspace)
        mock_session = AsyncMock()

        with patch(
            "pilot_space.infrastructure.database.repositories.project_member.ProjectMemberRepository.deactivate_all_for_user_in_workspace",
            new_callable=AsyncMock,
            return_value=0,
        ):
            result = await svc.remove_member(
                RemoveMemberPayload(
                    workspace_id=workspace.id,
                    target_user_id=member.id,
                    actor_id=admin.id,
                ),
                session=mock_session,
            )

        assert result.project_memberships_deactivated == 0

    @pytest.mark.asyncio
    async def test_project_cleanup_called_after_workspace_removal(self) -> None:
        """workspace_repo.remove_member is called before project membership deactivation."""
        workspace, admin, member = _make_workspace_with_admin_and_member()
        svc, mock_workspace_repo = _make_service(workspace)
        mock_session = AsyncMock()
        call_order: list[str] = []

        async def record_workspace_remove(*args, **kwargs):  # type: ignore[no-untyped-def]
            call_order.append("workspace_remove")
            return True

        mock_workspace_repo.remove_member.side_effect = record_workspace_remove

        with patch(
            "pilot_space.infrastructure.database.repositories.project_member.ProjectMemberRepository.deactivate_all_for_user_in_workspace",
            new_callable=AsyncMock,
        ) as mock_deactivate:

            async def record_project_deactivate(*args, **kwargs):  # type: ignore[no-untyped-def]
                call_order.append("project_deactivate")
                return 2

            mock_deactivate.side_effect = record_project_deactivate

            await svc.remove_member(
                RemoveMemberPayload(
                    workspace_id=workspace.id,
                    target_user_id=member.id,
                    actor_id=admin.id,
                ),
                session=mock_session,
            )

        assert call_order == ["workspace_remove", "project_deactivate"]
