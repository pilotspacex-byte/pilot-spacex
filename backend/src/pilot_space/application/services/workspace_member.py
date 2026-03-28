"""Workspace member management service.

CQRS-lite pattern (DD-064): list, update role, remove, profile + stats.
Source: FR-017, T020a (ownership transfer), M-5 (prevent owner self-removal).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from pilot_space.domain.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
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


# ===== Exception aliases for backward compatibility =====
# These names are kept so routers and tests can import them, but they now
# extend the shared domain hierarchy so the global app_error_handler catches them.

WorkspaceMemberError = AppError
WorkspaceNotFoundError = NotFoundError
WorkspaceMemberNotFoundError = NotFoundError
WorkspaceMemberForbiddenError = ForbiddenError
WorkspaceMemberConflictError = ConflictError
WorkspaceMemberValidationError = ValidationError


# ===== Payloads & Results =====


@dataclass
class ListMembersPayload:
    """Payload for listing workspace members."""

    workspace_id: UUID
    requesting_user_id: UUID
    project_id: UUID | None = None
    search: str | None = None
    role: str | None = None
    page: int = 1
    page_size: int = 20


@dataclass
class ListMembersResult:
    """Result of list_members operation."""

    members: list[WorkspaceMember]
    workspace: Workspace
    total: int = 0
    project_chips: dict[UUID, list[dict[str, Any]]] = field(default_factory=dict)


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
class BulkUpdateMemberAssignmentsPayload:
    """Payload for bulk-updating workspace role and/or project assignments."""

    workspace_id: UUID
    target_user_id: UUID
    requesting_user_id: UUID
    workspace_role: str | None = None
    project_assignments: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BulkUpdateMemberAssignmentsWarning:
    """Warning returned from bulk update operation."""

    code: str
    message: str


@dataclass
class BulkUpdateMemberAssignmentsResult:
    """Result of bulk_update_assignments operation."""

    user_id: UUID
    workspace_role: str
    project_assignments_updated: int
    warnings: list[BulkUpdateMemberAssignmentsWarning] = field(default_factory=list)


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
    project_memberships_deactivated: int = 0


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
        pm_repo: Any = None,
    ) -> ListMembersResult:
        """List workspace members with filtering, sorting, and pagination.

        Args:
            payload: List members payload with optional filters/pagination.
            pm_repo: ProjectMemberRepository for project_id filter and chip queries.

        Returns:
            Paginated list of workspace members with chips.
        """

        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")

        is_member = any(m.user_id == payload.requesting_user_id for m in (workspace.members or []))
        if not is_member:
            raise WorkspaceMemberForbiddenError("Not a member of this workspace")

        _ROLE_ORDER = {"owner": 1, "admin": 2, "member": 3, "guest": 4}

        members = sorted(
            workspace.members or [],
            key=lambda m: (
                _ROLE_ORDER.get(m.role.value.lower(), 5),
                m.created_at or "",
            ),
        )

        if payload.project_id is not None and pm_repo is not None:
            project_user_ids = {
                m.user_id
                for m in (
                    await pm_repo.list_members(payload.project_id, is_active=True, page_size=500)
                ).items
            }
            members = [m for m in members if m.user_id in project_user_ids]

        if payload.search:
            q = payload.search.lower()
            members = [
                m
                for m in members
                if m.user
                and (q in (m.user.full_name or "").lower() or q in (m.user.email or "").lower())
            ]

        if payload.role:
            role_lower = payload.role.lower()
            members = [m for m in members if m.role.value.lower() == role_lower]

        total = len(members)
        offset = (payload.page - 1) * payload.page_size
        page_members = members[offset : offset + payload.page_size]

        # Build project chips per page member
        project_chips: dict[UUID, list[dict[str, Any]]] = {}
        if pm_repo is not None:
            for member in page_members:
                chips = await pm_repo.get_project_chips_for_user(
                    payload.workspace_id, member.user_id
                )
                project_chips[member.user_id] = chips

        return ListMembersResult(
            members=page_members,
            workspace=workspace,
            total=total,
            project_chips=project_chips,
        )

    async def bulk_update_assignments(
        self,
        payload: BulkUpdateMemberAssignmentsPayload,
        session: AsyncSession,
    ) -> BulkUpdateMemberAssignmentsResult:
        """Bulk-update workspace role and/or project assignments for a member (FR-04).

        Requires caller to be ADMIN or OWNER of the workspace.
        Updating workspace_role to OWNER is restricted to current OWNERs.

        Args:
            payload: Bulk update payload.
            session: AsyncSession for workspace-role flush.

        Returns:
            BulkUpdateMemberAssignmentsResult with updated counts and warnings.

        Raises:
            ForbiddenError: If caller is not admin/owner or attempts invalid role upgrade.
            NotFoundError: If target member is not in the workspace.
            ValidationError: If a submitted project_id does not belong to this workspace.
        """
        from sqlalchemy import select as sa_select

        from pilot_space.application.services.project_member import (
            BulkUpdatePayload,
            ProjectMemberService,
            UnauthorizedError as PMUnauthorizedError,
        )
        from pilot_space.infrastructure.database.models.project import Project as ProjectModel
        from pilot_space.infrastructure.database.models.workspace_member import (
            WorkspaceRole as WsRole,
        )
        from pilot_space.infrastructure.database.repositories.project_member import (
            ProjectMemberRepository,
        )

        # Auth: caller must be ADMIN or OWNER
        from pilot_space.infrastructure.database.repositories.workspace_member_repository import (
            WorkspaceMemberRepository,
        )

        wm_repo = WorkspaceMemberRepository(session=session)
        caller = await wm_repo.get_by_user_workspace(
            payload.requesting_user_id, payload.workspace_id
        )
        if not caller or caller.role.value not in ("ADMIN", "OWNER"):
            raise WorkspaceMemberForbiddenError(
                "Only workspace admins or owners can modify assignments"
            )

        target = await wm_repo.get_by_user_workspace(payload.target_user_id, payload.workspace_id)
        if not target:
            raise WorkspaceMemberNotFoundError("Member not found in workspace")

        # Validate all submitted project_ids belong to this workspace
        if payload.project_assignments:
            submitted_ids = [UUID(str(a["project_id"])) for a in payload.project_assignments]
            rows = await session.execute(
                sa_select(ProjectModel.id).where(
                    ProjectModel.id.in_(submitted_ids),
                    ProjectModel.workspace_id == payload.workspace_id,
                    ProjectModel.is_deleted == False,  # noqa: E712
                )
            )
            found_ids = {row.id for row in rows.all()}
            invalid = [str(pid) for pid in submitted_ids if pid not in found_ids]
            if invalid:
                raise WorkspaceMemberValidationError(
                    f"Project(s) not found in workspace: {', '.join(invalid)}"
                )

        pm_repo = ProjectMemberRepository(session=session)
        pm_svc = ProjectMemberService(project_member_repository=pm_repo)

        try:
            pm_result = await pm_svc.bulk_update_assignments(
                BulkUpdatePayload(
                    workspace_id=payload.workspace_id,
                    target_user_id=payload.target_user_id,
                    requesting_user_id=payload.requesting_user_id,
                    requesting_user_role=caller.role.value,
                    current_workspace_role=target.role.value,
                    workspace_role=payload.workspace_role,
                    project_assignments=payload.project_assignments,
                )
            )
        except PMUnauthorizedError as e:
            raise WorkspaceMemberForbiddenError(str(e)) from e

        # Apply workspace role change if requested
        if payload.workspace_role and payload.workspace_role != target.role.value:
            try:
                new_role = WsRole(payload.workspace_role)
            except ValueError as e:
                raise WorkspaceMemberValidationError(
                    f"Invalid role: {payload.workspace_role}"
                ) from e

            # Guard: only OWNER can promote to OWNER
            if new_role == WsRole.OWNER and caller.role != WsRole.OWNER:
                raise WorkspaceMemberForbiddenError(
                    "Only the workspace owner can transfer ownership"
                )

            # Guard: prevent demoting the last admin
            new_role_is_non_admin = new_role not in (WsRole.OWNER, WsRole.ADMIN)
            if target.role in (WsRole.OWNER, WsRole.ADMIN) and new_role_is_non_admin:
                from sqlalchemy import func as sa_func

                from pilot_space.infrastructure.database.models.workspace_member import (
                    WorkspaceMember as WsMemberModel,
                )

                result = await session.execute(
                    sa_select(sa_func.count()).where(
                        WsMemberModel.workspace_id == payload.workspace_id,
                        WsMemberModel.role.in_([WsRole.OWNER, WsRole.ADMIN]),
                        WsMemberModel.is_deleted == False,  # noqa: E712
                    )
                )
                admin_count = result.scalar_one()
                if admin_count <= 1:
                    raise WorkspaceMemberConflictError(
                        "Cannot demote the only admin from workspace"
                    )

            target.role = new_role
            await session.flush()

        return BulkUpdateMemberAssignmentsResult(
            user_id=payload.target_user_id,
            workspace_role=pm_result.workspace_role or target.role.value,
            project_assignments_updated=pm_result.project_assignments_updated,
            warnings=[
                BulkUpdateMemberAssignmentsWarning(code=w.code, message=w.message)
                for w in pm_result.warnings
            ],
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
            raise WorkspaceMemberForbiddenError("Admin role required")

        # Guard: prevent owner from changing their own role (must use ownership transfer)
        if payload.actor_id == payload.target_user_id and actor_member.is_owner:
            raise WorkspaceMemberForbiddenError(
                "Cannot change own role. Use ownership transfer to reassign ownership."
            )

        target_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.target_user_id),
            None,
        )
        if not target_member:
            raise WorkspaceMemberNotFoundError("Member not found")

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
                raise WorkspaceMemberConflictError(msg)

        # Ownership transfer guard (FR-017, T020a)
        if new_role_enum == WorkspaceRole.OWNER:
            if not actor_member.is_owner:
                raise WorkspaceMemberForbiddenError(
                    "Only the workspace owner can transfer ownership"
                )

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
            raise WorkspaceMemberNotFoundError("Member not found")

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
        session: AsyncSession,
    ) -> RemoveMemberResult:
        """Remove member from workspace.

        Requires admin role (or self-removal).
        Constraints:
        - Owner cannot remove themselves (M-5)
        - Cannot remove the only admin

        Also deactivates all project memberships for the removed user within
        this workspace (same transaction).

        Args:
            payload: Remove member payload.
            session: AsyncSession for project membership cleanup.

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
            raise WorkspaceMemberForbiddenError("Admin role required to remove other members")

        # M-5 fix: prevent owner from removing themselves
        if is_self and actor_member and actor_member.is_owner:
            raise WorkspaceMemberForbiddenError(
                "Workspace owner cannot remove themselves. Transfer ownership first."
            )

        # Role-hierarchy guard: admins can only remove members with a lower role.
        # Owners can remove anyone (except themselves, caught above).
        target_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.target_user_id),
            None,
        )
        if (
            not is_self
            and actor_member is not None
            and not actor_member.is_owner
            and target_member is not None
            and target_member.is_admin
        ):
            raise WorkspaceMemberForbiddenError(
                "Admins cannot remove members with equal or higher role"
            )

        # Prevent removing the last admin/owner regardless of who initiates the removal
        if target_member and target_member.is_admin:
            admin_count = sum(1 for m in (workspace.members or []) if m.is_admin)
            if admin_count <= 1:
                raise WorkspaceMemberConflictError("Cannot remove the only admin from workspace")

        await self.workspace_repo.remove_member(
            payload.workspace_id,
            payload.target_user_id,
        )

        from pilot_space.infrastructure.database.repositories.project_member import (
            ProjectMemberRepository as _PMRepo,
        )

        _pm_repo = _PMRepo(session=session)
        _deactivated = await _pm_repo.deactivate_all_for_user_in_workspace(
            user_id=payload.target_user_id,
            workspace_id=payload.workspace_id,
        )
        logger.info(
            "Project memberships deactivated on workspace member removal",
            extra={"count": _deactivated, "user_id": str(payload.target_user_id)},
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
            project_memberships_deactivated=_deactivated,
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
            raise WorkspaceMemberForbiddenError(
                "Only admins or the member themselves can update availability"
            )

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
            raise WorkspaceMemberNotFoundError("Member not found")

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
            raise WorkspaceMemberForbiddenError("Not a member of this workspace")

        member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.user_id),
            None,
        )
        if not member:
            raise WorkspaceMemberNotFoundError("Member not found")

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
            raise WorkspaceMemberForbiddenError("Not a member of this workspace")

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
    "BulkUpdateMemberAssignmentsPayload",
    "BulkUpdateMemberAssignmentsResult",
    "BulkUpdateMemberAssignmentsWarning",
    "GetMemberActivityPayload",
    "GetMemberActivityResult",
    "GetMemberProfilePayload",
    "GetMemberProfileResult",
    "ListMembersPayload",
    "ListMembersResult",
    "MemberProfileService",
    "RemoveMemberPayload",
    "RemoveMemberResult",
    "UpdateMemberAvailabilityPayload",
    "UpdateMemberAvailabilityResult",
    "UpdateMemberRolePayload",
    "UpdateMemberRoleResult",
    "WorkspaceMemberConflictError",
    "WorkspaceMemberError",
    "WorkspaceMemberForbiddenError",
    "WorkspaceMemberNotFoundError",
    "WorkspaceMemberService",
    "WorkspaceMemberValidationError",
    "WorkspaceNotFoundError",
]
