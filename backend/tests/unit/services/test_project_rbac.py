"""Unit tests for ProjectRbacService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.application.services.project_rbac import ProjectRbacService
from pilot_space.domain.exceptions import ForbiddenError
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole


def _make_rbac_service(
    *,
    role: WorkspaceRole | None,
    active_membership: bool = False,
    assigned_project_ids: list[uuid.UUID] | None = None,
) -> tuple[ProjectRbacService, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Build a ProjectRbacService with mocked repositories.

    Returns:
        (service, project_id, workspace_id, user_id)
    """
    project_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()

    session = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = role
    session.execute = AsyncMock(return_value=scalar_result)

    project_member_repo = AsyncMock()
    project_member_repo.get_active_membership = AsyncMock(
        return_value=MagicMock() if active_membership else None
    )
    project_member_repo.list_project_ids_for_user = AsyncMock(
        return_value=assigned_project_ids or []
    )

    svc = ProjectRbacService(
        session=session,
        project_member_repository=project_member_repo,
    )
    return svc, project_id, workspace_id, user_id


class TestCheckProjectAccess:
    """Tests for ProjectRbacService.check_project_access."""

    @pytest.mark.asyncio
    async def test_owner_has_implicit_access(self) -> None:
        svc, project_id, workspace_id, user_id = _make_rbac_service(role=WorkspaceRole.OWNER)
        await svc.check_project_access(project_id, workspace_id, user_id)
        svc._project_member_repo.get_active_membership.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_has_implicit_access(self) -> None:
        svc, project_id, workspace_id, user_id = _make_rbac_service(role=WorkspaceRole.ADMIN)
        await svc.check_project_access(project_id, workspace_id, user_id)
        svc._project_member_repo.get_active_membership.assert_not_called()

    @pytest.mark.asyncio
    async def test_member_with_active_membership_allowed(self) -> None:
        svc, project_id, workspace_id, user_id = _make_rbac_service(
            role=WorkspaceRole.MEMBER, active_membership=True
        )
        await svc.check_project_access(project_id, workspace_id, user_id)

    @pytest.mark.asyncio
    async def test_member_without_membership_denied(self) -> None:
        svc, project_id, workspace_id, user_id = _make_rbac_service(
            role=WorkspaceRole.MEMBER, active_membership=False
        )
        with pytest.raises(ForbiddenError):
            await svc.check_project_access(project_id, workspace_id, user_id)

    @pytest.mark.asyncio
    async def test_guest_with_active_membership_allowed(self) -> None:
        svc, project_id, workspace_id, user_id = _make_rbac_service(
            role=WorkspaceRole.GUEST, active_membership=True
        )
        await svc.check_project_access(project_id, workspace_id, user_id)

    @pytest.mark.asyncio
    async def test_guest_without_membership_denied(self) -> None:
        svc, project_id, workspace_id, user_id = _make_rbac_service(
            role=WorkspaceRole.GUEST, active_membership=False
        )
        with pytest.raises(ForbiddenError):
            await svc.check_project_access(project_id, workspace_id, user_id)

    @pytest.mark.asyncio
    async def test_non_member_role_none_denied(self) -> None:
        """User not in workspace (role=None) is denied."""
        svc, project_id, workspace_id, user_id = _make_rbac_service(
            role=None, active_membership=False
        )
        with pytest.raises(ForbiddenError):
            await svc.check_project_access(project_id, workspace_id, user_id)


class TestGetAccessibleProjectIds:
    """Tests for ProjectRbacService.get_accessible_project_ids."""

    @pytest.mark.asyncio
    async def test_empty_candidates_returns_empty(self) -> None:
        svc, _, workspace_id, user_id = _make_rbac_service(role=WorkspaceRole.MEMBER)
        result = await svc.get_accessible_project_ids(workspace_id, user_id, [])
        assert result == set()

    @pytest.mark.asyncio
    async def test_admin_returns_all_candidates(self) -> None:
        ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        svc, _, workspace_id, user_id = _make_rbac_service(role=WorkspaceRole.ADMIN)
        result = await svc.get_accessible_project_ids(workspace_id, user_id, ids)
        assert result == set(ids)

    @pytest.mark.asyncio
    async def test_owner_returns_all_candidates(self) -> None:
        ids = [uuid.uuid4(), uuid.uuid4()]
        svc, _, workspace_id, user_id = _make_rbac_service(role=WorkspaceRole.OWNER)
        result = await svc.get_accessible_project_ids(workspace_id, user_id, ids)
        assert result == set(ids)

    @pytest.mark.asyncio
    async def test_member_returns_only_assigned_subset(self) -> None:
        ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        assigned = [ids[0], ids[2]]
        svc, _, workspace_id, user_id = _make_rbac_service(
            role=WorkspaceRole.MEMBER, assigned_project_ids=assigned
        )
        result = await svc.get_accessible_project_ids(workspace_id, user_id, ids)
        assert result == {ids[0], ids[2]}

    @pytest.mark.asyncio
    async def test_member_no_assignments_returns_empty(self) -> None:
        ids = [uuid.uuid4(), uuid.uuid4()]
        svc, _, workspace_id, user_id = _make_rbac_service(
            role=WorkspaceRole.MEMBER, assigned_project_ids=[]
        )
        result = await svc.get_accessible_project_ids(workspace_id, user_id, ids)
        assert result == set()

    @pytest.mark.asyncio
    async def test_guest_returns_only_assigned(self) -> None:
        ids = [uuid.uuid4(), uuid.uuid4()]
        svc, _, workspace_id, user_id = _make_rbac_service(
            role=WorkspaceRole.GUEST, assigned_project_ids=[ids[1]]
        )
        result = await svc.get_accessible_project_ids(workspace_id, user_id, ids)
        assert result == {ids[1]}


class TestCheckResourcePermission:
    """Tests for ProjectRbacService.check_resource_permission."""

    @pytest.mark.asyncio
    async def test_permission_granted_no_raise(self) -> None:
        svc, _, workspace_id, user_id = _make_rbac_service(role=WorkspaceRole.MEMBER)
        with patch(
            "pilot_space.application.services.project_rbac.check_permission",
            new=AsyncMock(return_value=True),
        ):
            await svc.check_resource_permission(user_id, workspace_id, "notes", "write")

    @pytest.mark.asyncio
    async def test_permission_denied_raises_forbidden(self) -> None:
        svc, _, workspace_id, user_id = _make_rbac_service(role=WorkspaceRole.GUEST)
        with (
            patch(
                "pilot_space.application.services.project_rbac.check_permission",
                new=AsyncMock(return_value=False),
            ),
            pytest.raises(ForbiddenError, match="Permission denied: notes:write"),
        ):
            await svc.check_resource_permission(user_id, workspace_id, "notes", "write")

    @pytest.mark.asyncio
    async def test_member_has_notes_write(self) -> None:
        svc, _, workspace_id, user_id = _make_rbac_service(role=WorkspaceRole.MEMBER)
        with patch(
            "pilot_space.application.services.project_rbac.check_permission",
            new=AsyncMock(return_value=True),
        ) as mock_check:
            await svc.check_resource_permission(user_id, workspace_id, "notes", "write")
            mock_check.assert_called_once_with(
                svc._session, user_id, workspace_id, "notes", "write"
            )

    @pytest.mark.asyncio
    async def test_guest_denied_notes_write(self) -> None:
        svc, _, workspace_id, user_id = _make_rbac_service(role=WorkspaceRole.GUEST)
        with (
            patch(
                "pilot_space.application.services.project_rbac.check_permission",
                new=AsyncMock(return_value=False),
            ),
            pytest.raises(ForbiddenError),
        ):
            await svc.check_resource_permission(user_id, workspace_id, "notes", "write")

    @pytest.mark.asyncio
    async def test_guest_denied_issues_write(self) -> None:
        svc, _, workspace_id, user_id = _make_rbac_service(role=WorkspaceRole.GUEST)
        with (
            patch(
                "pilot_space.application.services.project_rbac.check_permission",
                new=AsyncMock(return_value=False),
            ),
            pytest.raises(ForbiddenError, match="Permission denied: issues:write"),
        ):
            await svc.check_resource_permission(user_id, workspace_id, "issues", "write")
