"""Workspace member management service.

Handles member operations following CQRS-lite pattern (DD-064):
- List workspace members
- Update member role (with ownership transfer support)
- Remove member (with constraints)
- Member profile + contribution stats (MemberProfileService)

Source: FR-017, T020a (ownership transfer), M-5 (prevent owner self-removal).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from pilot_space.infrastructure.database.models.activity import Activity, ActivityType
from pilot_space.infrastructure.database.models.cycle import Cycle, CycleStatus
from pilot_space.infrastructure.database.models.integration import IntegrationLink
from pilot_space.infrastructure.database.models.issue import Issue
from pilot_space.infrastructure.database.models.state import State, StateGroup
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.database.repositories.audit_log_repository import (
    write_audit_nonfatal,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace import Workspace
    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
    )
    from pilot_space.infrastructure.database.repositories.audit_log_repository import (
        AuditLogRepository,
    )
    from pilot_space.infrastructure.database.repositories.workspace_repository import (
        WorkspaceRepository,
    )

logger = get_logger(__name__)


# ===== Custom Exceptions =====


class WorkspaceNotFoundError(ValueError):
    """Raised when the workspace does not exist."""


class MemberNotFoundError(ValueError):
    """Raised when the target member is not in the workspace."""


class UnauthorizedError(ValueError):
    """Raised when the actor lacks required permissions."""


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


@dataclass
class UpdateMemberAvailabilityPayload:
    """Payload for updating member weekly available hours."""

    workspace_id: UUID
    user_id: UUID
    actor_id: UUID
    weekly_available_hours: float  # must be 0..168


@dataclass
class UpdateMemberAvailabilityResult:
    """Result of update_availability operation."""

    member: WorkspaceMember


class WorkspaceMemberService:
    """Service for workspace member operations.

    Follows CQRS-lite pattern per DD-064.
    """

    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        self.workspace_repo = workspace_repo
        self._audit_repo = audit_log_repository

    async def list_members(
        self,
        payload: ListMembersPayload,
    ) -> ListMembersResult:
        """List workspace members with role info."""
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")

        is_member = any(m.user_id == payload.requesting_user_id for m in (workspace.members or []))
        if not is_member:
            raise UnauthorizedError("Not a member of this workspace")

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
            WorkspaceNotFoundError: If workspace not found.
            MemberNotFoundError: If target member not found.
            UnauthorizedError: If actor lacks required permissions.
        """
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")

        actor_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.actor_id),
            None,
        )
        if not actor_member or not actor_member.is_admin:
            raise UnauthorizedError("Admin role required")

        target_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.target_user_id),
            None,
        )
        if not target_member:
            raise MemberNotFoundError("Member not found")

        old_role = target_member.role.value
        new_role_enum = WorkspaceRole(payload.new_role)

        ownership_transferred = False

        # Last-admin guard: prevent demoting the only admin to a non-admin role
        target_is_admin = target_member.is_admin
        new_role_is_non_admin = new_role_enum not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN)
        if target_is_admin and new_role_is_non_admin:
            admin_count = sum(1 for m in (workspace.members or []) if m.is_admin)
            if admin_count <= 1:
                msg = "Cannot demote the only admin from workspace"
                raise ValueError(msg)

        # Ownership transfer guard (FR-017, T020a)
        if new_role_enum == WorkspaceRole.OWNER:
            if not actor_member.is_owner:
                raise UnauthorizedError("Only the workspace owner can transfer ownership")

            await self.workspace_repo.update_member_role(
                payload.workspace_id,
                payload.actor_id,
                WorkspaceRole.ADMIN,
            )
            ownership_transferred = True

        updated_member = await self.workspace_repo.update_member_role(
            payload.workspace_id,
            payload.target_user_id,
            new_role_enum,
        )

        if not updated_member:
            raise MemberNotFoundError("Member not found")

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

        await write_audit_nonfatal(
            self._audit_repo,
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            action="member.role_changed",
            resource_type="member",
            resource_id=payload.target_user_id,
            payload={"before": {"role": old_role}, "after": {"role": payload.new_role}},
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
            WorkspaceNotFoundError: If workspace not found.
            MemberNotFoundError: If target not found.
            UnauthorizedError: If actor lacks permissions or constraint violated.
        """
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")

        actor_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.actor_id),
            None,
        )
        is_admin = actor_member is not None and actor_member.is_admin
        is_self = payload.target_user_id == payload.actor_id

        if not (is_admin or is_self):
            raise UnauthorizedError("Admin role required to remove other members")

        # M-5 fix: prevent owner from removing themselves
        if is_self and actor_member and actor_member.is_owner:
            raise UnauthorizedError(
                "Workspace owner cannot remove themselves. Transfer ownership first."
            )

        # Prevent removing the last admin/owner regardless of who initiates the removal
        target_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.target_user_id),
            None,
        )
        if target_member and target_member.is_admin:
            admin_count = sum(1 for m in (workspace.members or []) if m.is_admin)
            if admin_count <= 1:
                raise UnauthorizedError("Cannot remove the only admin from workspace")

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

        await write_audit_nonfatal(
            self._audit_repo,
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            action="member.removed",
            resource_type="member",
            resource_id=payload.target_user_id,
            payload={"before": {"user_id": str(payload.target_user_id)}, "after": {}},
        )

        return RemoveMemberResult(
            removed_user_id=payload.target_user_id,
            workspace_id=payload.workspace_id,
            removed_at=datetime.now(tz=UTC),
        )

    async def update_availability(
        self,
        payload: UpdateMemberAvailabilityPayload,
        session: AsyncSession,
    ) -> UpdateMemberAvailabilityResult:
        """Update weekly available hours. Self or admin only."""
        from pilot_space.infrastructure.database.models.workspace_member import (
            WorkspaceMember as WMModel,
        )
        from pilot_space.infrastructure.database.rls import set_rls_context

        await set_rls_context(session, payload.actor_id, payload.workspace_id)
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")

        actor_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.actor_id), None
        )
        is_self = payload.actor_id == payload.user_id
        is_admin = actor_member is not None and actor_member.is_admin

        if not (is_self or is_admin):
            raise UnauthorizedError("Only admins or the member themselves can update availability")

        result = await session.execute(
            select(WMModel)
            .options(selectinload(WMModel.user))
            .where(
                WMModel.workspace_id == payload.workspace_id,
                WMModel.user_id == payload.user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise MemberNotFoundError("Member not found")

        member.weekly_available_hours = payload.weekly_available_hours
        await session.flush()
        await session.refresh(member)
        return UpdateMemberAvailabilityResult(member=member)


@dataclass
class GetMemberProfilePayload:
    """Payload for getting member profile with stats."""

    workspace_id: UUID
    user_id: UUID
    requesting_user_id: UUID


@dataclass
class GetMemberProfileResult:
    """Result of get_profile — member + computed stats."""

    member: WorkspaceMember
    issues_created: int
    issues_assigned: int
    cycle_velocity: float
    capacity_utilization_pct: float
    pr_commit_links_count: int


@dataclass
class GetMemberActivityPayload:
    """Payload for paginated member activity."""

    workspace_id: UUID
    user_id: UUID
    requesting_user_id: UUID
    page: int = 1
    page_size: int = 20
    type_filter: ActivityType | None = None


@dataclass
class GetMemberActivityResult:
    """Paginated activity result."""

    items: list[Activity] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class MemberProfileService:
    """Service for member profile + contribution stats.

    Computes all 5 stats using asyncio.gather for parallelism (no N+1):
    - issues_created: single COUNT with reporter_id filter
    - issues_assigned: single COUNT with assignee_id filter
    - cycle_velocity: 2 queries (last-3 cycle IDs, then count closed issues)
    - capacity_utilization_pct: 2 queries (active cycle ID, then sum estimate_hours)
    - pr_commit_links_count: single COUNT with JOIN to issues
    """

    def __init__(
        self,
        session: AsyncSession,
        workspace_repo: WorkspaceRepository,
    ) -> None:
        self.session = session
        self.workspace_repo = workspace_repo

    async def get_profile(
        self,
        payload: GetMemberProfilePayload,
    ) -> GetMemberProfileResult:
        """Fetch member + compute contribution stats.

        Args:
            payload: Profile request payload.

        Returns:
            Member with aggregated stats.

        Raises:
            WorkspaceNotFoundError: If workspace not found.
            UnauthorizedError: If requester is not a workspace member.
            MemberNotFoundError: If target member not found.
        """
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")

        is_member = any(m.user_id == payload.requesting_user_id for m in (workspace.members or []))
        if not is_member:
            raise UnauthorizedError("Not a member of this workspace")

        member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.user_id),
            None,
        )
        if not member:
            raise MemberNotFoundError("Member not found")

        # Group 1: all independent queries run in parallel
        (
            created_result,
            assigned_result,
            cycle_ids_result,
            active_cycle_result,
            pr_result,
        ) = await asyncio.gather(
            self.session.execute(
                select(func.count(Issue.id)).where(
                    and_(
                        Issue.workspace_id == payload.workspace_id,
                        Issue.reporter_id == payload.user_id,
                        Issue.is_deleted == False,  # noqa: E712
                    )
                )
            ),
            self.session.execute(
                select(func.count(Issue.id)).where(
                    and_(
                        Issue.workspace_id == payload.workspace_id,
                        Issue.assignee_id == payload.user_id,
                        Issue.is_deleted == False,  # noqa: E712
                    )
                )
            ),
            self.session.execute(
                select(Cycle.id)
                .where(
                    and_(
                        Cycle.workspace_id == payload.workspace_id,
                        Cycle.status == CycleStatus.COMPLETED,
                        Cycle.is_deleted == False,  # noqa: E712
                    )
                )
                .order_by(Cycle.end_date.desc())
                .limit(3)
            ),
            self.session.execute(
                select(Cycle.id)
                .where(
                    and_(
                        Cycle.workspace_id == payload.workspace_id,
                        Cycle.status == CycleStatus.ACTIVE,
                        Cycle.is_deleted == False,  # noqa: E712
                    )
                )
                .limit(1)
            ),
            self.session.execute(
                select(func.count(IntegrationLink.id))
                .join(Issue, IntegrationLink.issue_id == Issue.id)
                .where(
                    and_(
                        or_(
                            Issue.assignee_id == payload.user_id,
                            Issue.reporter_id == payload.user_id,
                        ),
                        Issue.workspace_id == payload.workspace_id,
                        Issue.is_deleted == False,  # noqa: E712
                        IntegrationLink.is_deleted == False,  # noqa: E712
                    )
                )
            ),
        )

        issues_created = created_result.scalar() or 0
        issues_assigned = assigned_result.scalar() or 0
        cycle_ids = cycle_ids_result.scalars().all()
        active_cycle_id = active_cycle_result.scalar()
        pr_commit_links_count = pr_result.scalar() or 0

        # Group 2: dependent queries run in parallel after group 1
        async def _get_cycle_closed_count() -> int:
            if not cycle_ids:
                return 0
            closed_result = await self.session.execute(
                select(func.count(Issue.id))
                .join(State, Issue.state_id == State.id)
                .where(
                    and_(
                        Issue.cycle_id.in_(cycle_ids),
                        Issue.assignee_id == payload.user_id,
                        Issue.is_deleted == False,  # noqa: E712
                        State.group == StateGroup.COMPLETED,
                    )
                )
            )
            return closed_result.scalar() or 0

        async def _get_committed_hours() -> float:
            if not active_cycle_id:
                return 0.0
            committed_result = await self.session.execute(
                select(func.coalesce(func.sum(Issue.estimate_hours), 0.0)).where(
                    and_(
                        Issue.cycle_id == active_cycle_id,
                        Issue.assignee_id == payload.user_id,
                        Issue.is_deleted == False,  # noqa: E712
                    )
                )
            )
            return float(committed_result.scalar() or 0.0)

        total_closed, committed_hours = await asyncio.gather(
            _get_cycle_closed_count(),
            _get_committed_hours(),
        )

        cycle_velocity = total_closed / len(cycle_ids) if cycle_ids else 0.0
        available = float(member.weekly_available_hours or 40.0)
        utilization = min(100.0, committed_hours / available * 100.0) if available > 0 else 0.0

        return GetMemberProfileResult(
            member=member,
            issues_created=issues_created,
            issues_assigned=issues_assigned,
            cycle_velocity=cycle_velocity,
            capacity_utilization_pct=utilization,
            pr_commit_links_count=pr_commit_links_count,
        )

    async def get_activity(
        self,
        payload: GetMemberActivityPayload,
    ) -> GetMemberActivityResult:
        """Fetch paginated activity stream for a member.

        Args:
            payload: Activity request payload.

        Returns:
            Paginated list of Activity ORM objects.

        Raises:
            WorkspaceNotFoundError: If workspace not found.
            UnauthorizedError: If requester is not authorized.
        """
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")

        is_member = any(m.user_id == payload.requesting_user_id for m in (workspace.members or []))
        if not is_member:
            raise UnauthorizedError("Not a member of this workspace")

        page_size = min(payload.page_size, 50)
        offset = (payload.page - 1) * page_size

        base_filter = and_(
            Activity.workspace_id == payload.workspace_id,
            Activity.actor_id == payload.user_id,
            Activity.is_deleted == False,  # noqa: E712
        )
        if payload.type_filter:
            base_filter = and_(
                base_filter,
                Activity.activity_type == payload.type_filter,
            )

        total_result = await self.session.execute(
            select(func.count(Activity.id)).where(base_filter)
        )
        total = total_result.scalar() or 0

        items_result = await self.session.execute(
            select(Activity)
            .options(
                joinedload(Activity.issue),
                joinedload(Activity.actor),
            )
            .where(base_filter)
            .order_by(Activity.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(items_result.unique().scalars().all())

        return GetMemberActivityResult(
            items=items,
            total=total,
            page=payload.page,
            page_size=page_size,
        )


__all__ = [
    "GetMemberActivityPayload",
    "GetMemberActivityResult",
    "GetMemberProfilePayload",
    "GetMemberProfileResult",
    "ListMembersPayload",
    "ListMembersResult",
    "MemberNotFoundError",
    "MemberProfileService",
    "RemoveMemberPayload",
    "RemoveMemberResult",
    "UnauthorizedError",
    "UpdateMemberAvailabilityPayload",
    "UpdateMemberAvailabilityResult",
    "UpdateMemberRolePayload",
    "UpdateMemberRoleResult",
    "WorkspaceMemberService",
    "WorkspaceNotFoundError",
]
