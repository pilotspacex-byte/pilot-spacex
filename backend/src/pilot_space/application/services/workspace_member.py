"""Workspace member management service.

Handles member operations following CQRS-lite pattern (DD-064):
- List workspace members
- Update member role (with ownership transfer support)
- Remove member (with constraints)

Source: FR-017, T020a (ownership transfer), M-5 (prevent owner self-removal).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace import Workspace
    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
    )
    from pilot_space.infrastructure.database.repositories.workspace_repository import (
        WorkspaceRepository,
    )

logger = get_logger(__name__)


# ===== Payloads & Results =====


@dataclass
class ListMembersPayload:
    """Payload for listing workspace members."""

    workspace_id: UUID
    requesting_user_id: UUID


@dataclass
class ListMembersResult:
    """Result of list_members operation."""

    members: list[WorkspaceMember]
    workspace: Workspace


@dataclass
class UpdateMemberRolePayload:
    """Payload for updating member role."""

    workspace_id: UUID
    target_user_id: UUID
    new_role: str  # admin, member, guest, owner
    actor_id: UUID


@dataclass
class UpdateMemberRoleResult:
    """Result of update_member_role operation."""

    updated_member: WorkspaceMember
    old_role: str
    new_role: str
    ownership_transferred: bool = False


@dataclass
class RemoveMemberPayload:
    """Payload for removing workspace member."""

    workspace_id: UUID
    target_user_id: UUID
    actor_id: UUID


@dataclass
class RemoveMemberResult:
    """Result of remove_member operation."""

    removed_user_id: UUID
    workspace_id: UUID
    removed_at: datetime


class WorkspaceMemberService:
    """Service for workspace member operations.

    Follows CQRS-lite pattern per DD-064.
    """

    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
    ) -> None:
        self.workspace_repo = workspace_repo

    async def list_members(
        self,
        payload: ListMembersPayload,
    ) -> ListMembersResult:
        """List workspace members with role info.

        Args:
            payload: List members payload.

        Returns:
            List of workspace members.

        Raises:
            ValueError: If workspace not found or user not member.
        """
        # H-1/H-2 fix: use get_with_members to eagerly load members
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            msg = "Workspace not found"
            raise ValueError(msg)

        # Check membership
        is_member = any(m.user_id == payload.requesting_user_id for m in (workspace.members or []))
        if not is_member:
            msg = "Not a member of this workspace"
            raise ValueError(msg)

        return ListMembersResult(
            members=workspace.members or [],
            workspace=workspace,
        )

    async def update_member_role(
        self,
        payload: UpdateMemberRolePayload,
    ) -> UpdateMemberRoleResult:
        """Update member role (requires admin).

        Handles ownership transfer: when promoting to owner, current owner
        is demoted to admin automatically (FR-017, T020a).

        Args:
            payload: Update member role payload.

        Returns:
            Updated member with old/new roles.

        Raises:
            ValueError: If not found, not authorized, or invalid operation.
        """
        # H-1 fix: use get_with_members to eagerly load members
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            msg = "Workspace not found"
            raise ValueError(msg)

        # Check actor is admin
        actor_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.actor_id),
            None,
        )
        if not actor_member or not actor_member.is_admin:
            msg = "Admin role required"
            raise ValueError(msg)

        # Find target member
        target_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.target_user_id),
            None,
        )
        if not target_member:
            msg = "Member not found"
            raise ValueError(msg)

        old_role = target_member.role.value
        new_role_enum = WorkspaceRole(payload.new_role)

        ownership_transferred = False

        # Ownership transfer guard (FR-017, T020a)
        if new_role_enum == WorkspaceRole.OWNER:
            if not actor_member.is_owner:
                msg = "Only the workspace owner can transfer ownership"
                raise ValueError(msg)

            # Demote current owner to admin
            await self.workspace_repo.update_member_role(
                payload.workspace_id,
                payload.actor_id,
                WorkspaceRole.ADMIN,
            )
            ownership_transferred = True

        # Update target member role
        updated_member = await self.workspace_repo.update_member_role(
            payload.workspace_id,
            payload.target_user_id,
            new_role_enum,
        )

        if not updated_member:
            msg = "Member not found"
            raise ValueError(msg)

        logger.info(
            "Member role updated",
            extra={
                "workspace_id": str(payload.workspace_id),
                "target_user_id": str(payload.target_user_id),
                "old_role": old_role,
                "new_role": payload.new_role,
                "ownership_transferred": ownership_transferred,
            },
        )

        return UpdateMemberRoleResult(
            updated_member=updated_member,
            old_role=old_role,
            new_role=payload.new_role,
            ownership_transferred=ownership_transferred,
        )

    async def remove_member(
        self,
        payload: RemoveMemberPayload,
    ) -> RemoveMemberResult:
        """Remove member from workspace.

        Requires admin role (or self-removal).
        Constraints:
        - Owner cannot remove themselves (M-5)
        - Cannot remove the only admin

        Args:
            payload: Remove member payload.

        Returns:
            Removed member info.

        Raises:
            ValueError: If not found, not authorized, or violates constraints.
        """
        # H-2 fix: use get_with_members to eagerly load members
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            msg = "Workspace not found"
            raise ValueError(msg)

        # Check authorization (admin/owner or self)
        actor_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.actor_id),
            None,
        )
        is_admin = actor_member is not None and actor_member.is_admin
        is_self = payload.target_user_id == payload.actor_id

        if not (is_admin or is_self):
            msg = "Admin role required to remove other members"
            raise ValueError(msg)

        # M-5 fix: prevent owner from removing themselves
        if is_self and actor_member and actor_member.is_owner:
            msg = "Workspace owner cannot remove themselves. Transfer ownership first."
            raise ValueError(msg)

        # Prevent removing the only admin/owner
        if is_self and is_admin:
            admin_count = sum(1 for m in (workspace.members or []) if m.is_admin)
            if admin_count == 1:
                msg = "Cannot remove the only admin from workspace"
                raise ValueError(msg)

        await self.workspace_repo.remove_member(
            payload.workspace_id,
            payload.target_user_id,
        )

        logger.info(
            "Workspace member removed",
            extra={
                "workspace_id": str(payload.workspace_id),
                "user_id": str(payload.target_user_id),
            },
        )

        return RemoveMemberResult(
            removed_user_id=payload.target_user_id,
            workspace_id=payload.workspace_id,
            removed_at=datetime.now(tz=UTC),
        )


__all__ = [
    "ListMembersPayload",
    "ListMembersResult",
    "RemoveMemberPayload",
    "RemoveMemberResult",
    "UpdateMemberRolePayload",
    "UpdateMemberRoleResult",
    "WorkspaceMemberService",
]
