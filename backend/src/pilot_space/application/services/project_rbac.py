"""Centralized project-level RBAC service.

Handles workspace role checks, project membership gates, and resource
permission enforcement for write operations.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import ForbiddenError
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.database.permissions import check_permission
from pilot_space.infrastructure.database.repositories.project_member import (
    ProjectMemberRepository,
)


class ProjectRbacService:
    """Service for project-level RBAC enforcement.

    Centralizes workspace role lookups, project membership gates, and
    resource permission checks that span multiple routers.
    """

    def __init__(
        self,
        session: AsyncSession,
        project_member_repository: ProjectMemberRepository,
    ) -> None:
        self._session = session
        self._project_member_repo = project_member_repository

    async def _get_workspace_role(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceRole | None:
        """Return the workspace role for a user, or None if not a member."""
        from sqlalchemy import select

        from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember

        result = await self._session.execute(
            select(WorkspaceMember.role).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def check_project_access(
        self,
        project_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> None:
        """Verify user can access a project based on workspace role.

        ADMIN/OWNER have implicit access to all projects.
        MEMBER/GUEST require an active project_members row.

        Raises:
            ForbiddenError: If MEMBER/GUEST without active project membership.
        """
        role = await self._get_workspace_role(workspace_id, user_id)
        if role in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER):
            return

        membership = await self._project_member_repo.get_active_membership(project_id, user_id)
        if not membership:
            raise ForbiddenError("Project access denied")

    async def get_accessible_project_ids(
        self,
        workspace_id: UUID,
        user_id: UUID,
        candidate_ids: list[UUID],
    ) -> set[UUID]:
        """Return the subset of candidate_ids the user can access.

        ADMIN/OWNER: all candidates returned.
        MEMBER/GUEST: only projects where an active membership row exists.

        Returns:
            Set of accessible project IDs.
        """
        if not candidate_ids:
            return set()

        role = await self._get_workspace_role(workspace_id, user_id)
        if role in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER):
            return set(candidate_ids)

        assigned = await self._project_member_repo.list_project_ids_for_user(user_id)
        return set(candidate_ids) & set(assigned)

    async def get_my_project_ids(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[UUID] | None:
        """Return project IDs the user can access, or None if unrestricted.

        ADMIN/OWNER: returns None (no filter — can access all projects).
        MEMBER/GUEST: returns their assigned project IDs (may be empty list).
        """
        role = await self._get_workspace_role(workspace_id, user_id)
        if role in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER):
            return None
        return await self._project_member_repo.list_project_ids_for_user(user_id)

    async def check_resource_permission(
        self,
        user_id: UUID,
        workspace_id: UUID,
        resource: str,
        action: str,
    ) -> None:
        """Verify user has resource:action permission in workspace.

        Thin adapter over check_permission(); respects custom roles and
        built-in role capability map.

        Raises:
            ForbiddenError: If the user lacks the specified permission.
        """
        allowed = await check_permission(self._session, user_id, workspace_id, resource, action)
        if not allowed:
            raise ForbiddenError(f"Permission denied: {resource}:{action}")


__all__ = ["ProjectRbacService"]
