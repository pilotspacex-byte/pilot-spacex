"""RbacService — custom role management for AUTH-05.

Provides CRUD for custom roles and custom role assignment to workspace members.
Permission string validation is enforced on create/update.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.infrastructure.database.models.custom_role import CustomRole
from pilot_space.infrastructure.database.permissions import ACTIONS, RESOURCES

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember
    from pilot_space.infrastructure.database.repositories.audit_log_repository import (
        AuditLogRepository,
    )
    from pilot_space.infrastructure.database.repositories.custom_role_repository import (
        CustomRoleRepository,
    )
    from pilot_space.infrastructure.database.repositories.workspace_member_repository import (
        WorkspaceMemberRepository,
    )


# ---------------------------------------------------------------------------
# Domain errors
# ---------------------------------------------------------------------------


class DuplicateRoleNameError(ValueError):
    """Raised when a custom role name already exists within the workspace."""


class RoleNotFoundError(ValueError):
    """Raised when a custom role cannot be found in the workspace."""


class MemberNotFoundError(ValueError):
    """Raised when a workspace member cannot be found."""


# ---------------------------------------------------------------------------
# Permission validation helpers
# ---------------------------------------------------------------------------


def _validate_permissions(permissions: list[str]) -> None:
    """Validate that all permission strings are valid resource:action pairs.

    Args:
        permissions: List of permission strings e.g. ["issues:read", "notes:write"].

    Raises:
        ValueError: If any string does not match a known resource:action combo.
    """
    for perm in permissions:
        parts = perm.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"invalid permission string '{perm}': must be 'resource:action'")
        resource, action = parts
        if resource not in RESOURCES:
            raise ValueError(
                f"invalid permission '{perm}': unknown resource '{resource}'. "
                f"Known resources: {sorted(RESOURCES)}"
            )
        if action not in ACTIONS:
            raise ValueError(
                f"invalid permission '{perm}': unknown action '{action}'. "
                f"Known actions: {sorted(ACTIONS)}"
            )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RbacService:
    """Service for custom role CRUD and member role assignment.

    Attributes:
        custom_role_repo: Repository for custom_roles table.
        workspace_member_repo: Repository for workspace_members table (RBAC ops).
    """

    def __init__(
        self,
        custom_role_repo: CustomRoleRepository,
        workspace_member_repo: WorkspaceMemberRepository,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        self.custom_role_repo = custom_role_repo
        self.workspace_member_repo = workspace_member_repo
        self._audit_repo = audit_log_repository

    async def create_role(
        self,
        workspace_id: UUID,
        name: str,
        description: str | None,
        permissions: list[str],
        session: AsyncSession,
        actor_id: UUID | None = None,
    ) -> CustomRole:
        """Create a new custom role in the workspace.

        Args:
            workspace_id: Owning workspace.
            name: Role name (unique per workspace).
            description: Optional human-readable description.
            permissions: List of permission strings (validated).
            session: Async DB session.

        Returns:
            The created CustomRole.

        Raises:
            DuplicateRoleNameError: If a role with this name already exists.
            ValueError: If any permission string is invalid.
        """
        _validate_permissions(permissions)

        existing = await self.custom_role_repo.get_by_name(workspace_id, name)
        if existing is not None:
            raise DuplicateRoleNameError(
                f"A custom role named '{name}' already exists in this workspace."
            )

        role = CustomRole(
            workspace_id=workspace_id,
            name=name,
            description=description,
            permissions=permissions,
        )
        created = await self.custom_role_repo.create(role)

        # Write audit log entry (non-fatal)
        if self._audit_repo is not None:
            try:
                from pilot_space.infrastructure.database.models.audit_log import ActorType

                await self._audit_repo.create(
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    actor_type=ActorType.USER,
                    action="custom_role.create",
                    resource_type="custom_role",
                    resource_id=created.id,
                    payload={
                        "before": {},
                        "after": {
                            "name": created.name,
                            "permissions": created.permissions or [],
                        },
                    },
                    ip_address=None,
                )
            except Exception as exc:
                import logging

                logging.getLogger(__name__).warning(
                    "RbacService.create_role: failed to write audit log: %s", exc
                )

        return created

    async def list_roles(
        self,
        workspace_id: UUID,
        session: AsyncSession,
    ) -> Sequence[CustomRole]:
        """List all custom roles for a workspace.

        Args:
            workspace_id: Owning workspace.
            session: Async DB session (not used directly; repo holds session ref).

        Returns:
            Sequence of CustomRole objects.
        """
        return await self.custom_role_repo.list_for_workspace(workspace_id)

    async def get_role(
        self,
        role_id: UUID,
        workspace_id: UUID,
        session: AsyncSession,
    ) -> CustomRole | None:
        """Get a single custom role by ID, scoped to workspace.

        Args:
            role_id: Role UUID.
            workspace_id: Owning workspace UUID.
            session: Async DB session.

        Returns:
            CustomRole or None if not found.
        """
        return await self.custom_role_repo.get(role_id, workspace_id)

    async def update_role(
        self,
        role_id: UUID,
        workspace_id: UUID,
        name: str | None,
        description: str | None,
        permissions: list[str] | None,
        session: AsyncSession,
        actor_id: UUID | None = None,
    ) -> CustomRole:
        """Partially update a custom role (only update provided fields).

        Args:
            role_id: Role UUID.
            workspace_id: Owning workspace UUID.
            name: New name, or None to keep existing.
            description: New description, or None to keep existing.
            permissions: New permissions list, or None to keep existing.
            session: Async DB session.

        Returns:
            Updated CustomRole.

        Raises:
            RoleNotFoundError: If the role does not exist.
            DuplicateRoleNameError: If the new name conflicts with an existing role.
            ValueError: If any permission string is invalid.
        """
        role = await self.custom_role_repo.get(role_id, workspace_id)
        if role is None:
            raise RoleNotFoundError(f"Custom role {role_id} not found in workspace.")

        if name is not None and name != role.name:
            conflict = await self.custom_role_repo.get_by_name(
                workspace_id, name, exclude_id=role_id
            )
            if conflict is not None:
                raise DuplicateRoleNameError(
                    f"A custom role named '{name}' already exists in this workspace."
                )
            role.name = name

        if description is not None:
            role.description = description

        if permissions is not None:
            _validate_permissions(permissions)
            role.permissions = permissions

        updated = await self.custom_role_repo.update(role)

        # Write audit log entry (non-fatal)
        if self._audit_repo is not None:
            try:
                from pilot_space.infrastructure.database.models.audit_log import ActorType

                await self._audit_repo.create(
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    actor_type=ActorType.USER,
                    action="custom_role.update",
                    resource_type="custom_role",
                    resource_id=role_id,
                    payload={
                        "changed_fields": [
                            k
                            for k, v in [
                                ("name", name),
                                ("description", description),
                                ("permissions", permissions),
                            ]
                            if v is not None
                        ]
                    },
                    ip_address=None,
                )
            except Exception as exc:
                import logging

                logging.getLogger(__name__).warning(
                    "RbacService.update_role: failed to write audit log: %s", exc
                )

        return updated

    async def delete_role(
        self,
        role_id: UUID,
        workspace_id: UUID,
        session: AsyncSession,
        actor_id: UUID | None = None,
    ) -> None:
        """Soft-delete a custom role.

        Before deleting, clears custom_role_id from all members assigned this
        role to prevent orphaned references.

        Args:
            role_id: Role UUID.
            workspace_id: Owning workspace UUID.
            session: Async DB session.

        Raises:
            RoleNotFoundError: If the role does not exist.
        """
        role = await self.custom_role_repo.get(role_id, workspace_id)
        if role is None:
            raise RoleNotFoundError(f"Custom role {role_id} not found in workspace.")

        # Clear member assignments first to prevent orphaned FK references
        await self.workspace_member_repo.clear_custom_role_assignments(
            role_id=role_id, session=session
        )

        # Capture name before deletion for audit payload
        role_name = role.name

        await self.custom_role_repo.soft_delete(role_id, workspace_id)

        # Write audit log entry (non-fatal)
        if self._audit_repo is not None:
            try:
                from pilot_space.infrastructure.database.models.audit_log import ActorType

                await self._audit_repo.create(
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    actor_type=ActorType.USER,
                    action="custom_role.delete",
                    resource_type="custom_role",
                    resource_id=role_id,
                    payload={"before": {"name": role_name}, "after": {}},
                    ip_address=None,
                )
            except Exception as exc:
                import logging

                logging.getLogger(__name__).warning(
                    "RbacService.delete_role: failed to write audit log: %s", exc
                )

    async def assign_role_to_member(
        self,
        user_id: UUID,
        workspace_id: UUID,
        custom_role_id: UUID | None,
        session: AsyncSession,
    ) -> WorkspaceMember:
        """Assign or unassign a custom role for a workspace member.

        Passing custom_role_id=None clears the custom role, reverting the member
        to their built-in WorkspaceRole permissions.

        Args:
            user_id: Member user UUID.
            workspace_id: Workspace UUID.
            custom_role_id: Custom role to assign, or None to clear.
            session: Async DB session.

        Returns:
            Updated WorkspaceMember.

        Raises:
            MemberNotFoundError: If the user is not a member of the workspace.
        """
        member = await self.workspace_member_repo.get_by_user_workspace(user_id, workspace_id)
        if member is None:
            raise MemberNotFoundError(
                f"User {user_id} is not a member of workspace {workspace_id}."
            )

        member.custom_role_id = custom_role_id
        return await self.workspace_member_repo.update(member)


__all__ = [
    "DuplicateRoleNameError",
    "MemberNotFoundError",
    "RbacService",
    "RoleNotFoundError",
]
