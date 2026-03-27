"""ProjectMemberService — application-layer logic for project-scoped RBAC.

Handles add/remove/list member operations, bulk reassignment,
my-projects dashboard query, and invite-acceptance materialisation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from pilot_space.infrastructure.database.models.project_member import ProjectMember
from pilot_space.infrastructure.database.repositories.project_member import (
    ProjectMemberRepository,
)

logger = logging.getLogger(__name__)


# ── Errors ────────────────────────────────────────────────────────────────────


class ProjectMemberError(Exception):
    """Base error for project member operations."""


class ProjectNotFoundError(ProjectMemberError):
    """Raised when the project does not exist in the workspace."""


class UserNotWorkspaceMemberError(ProjectMemberError):
    """Raised when the target user is not a workspace member."""


class AlreadyProjectMemberError(ProjectMemberError):
    """Raised when the user is already an active project member."""


class NotProjectMemberError(ProjectMemberError):
    """Raised when attempting to remove a non-member."""


class UnauthorizedError(ProjectMemberError):
    """Raised when the requesting user lacks admin/owner rights."""


# ── Payloads ──────────────────────────────────────────────────────────────────


@dataclass
class AddMemberPayload:
    workspace_id: UUID
    project_id: UUID
    user_id: UUID
    requesting_user_id: UUID
    requesting_user_role: str  # workspace role of requester


@dataclass
class RemoveMemberPayload:
    workspace_id: UUID
    project_id: UUID
    user_id: UUID
    requesting_user_id: UUID
    requesting_user_role: str


@dataclass
class ListMembersPayload:
    project_id: UUID
    search: str | None = None
    is_active: bool | None = True
    cursor: str | None = None
    page_size: int = 20


@dataclass
class BulkUpdatePayload:
    workspace_id: UUID
    target_user_id: UUID
    requesting_user_id: UUID
    requesting_user_role: str
    current_workspace_role: str
    workspace_role: str | None = None  # new role if changing
    project_assignments: list[dict[str, Any]] = field(
        default_factory=list
    )  # [{project_id, action}]


@dataclass
class InviteAssignmentsPayload:
    workspace_id: UUID
    user_id: UUID
    assigned_by: UUID | None
    project_assignments: list[dict[str, Any]]  # [{project_id, role}]


# ── Results ───────────────────────────────────────────────────────────────────


@dataclass
class ListMembersResult:
    members: list[ProjectMember]
    total: int
    next_cursor: str | None = None
    has_next: bool = False


@dataclass
class BulkUpdateWarning:
    code: str
    message: str


@dataclass
class BulkUpdateResult:
    user_id: UUID
    workspace_role: str | None
    project_assignments_updated: int
    warnings: list[BulkUpdateWarning] = field(default_factory=list)


@dataclass
class MyProjectEntry:
    project_id: UUID
    name: str
    identifier: str
    description: str | None
    icon: str | None
    is_archived: bool
    role: str
    assigned_at: datetime | None
    last_activity_at: datetime | None
    open_issues_count: int
    total_issues_count: int


@dataclass
class MyProjectsResult:
    items: list[MyProjectEntry]
    total: int


# ── Service ───────────────────────────────────────────────────────────────────


class ProjectMemberService:
    """Application-layer service for project-scoped RBAC operations."""

    def __init__(self, project_member_repository: ProjectMemberRepository) -> None:
        self._repo = project_member_repository

    def _require_admin(self, role: str, action: str = "manage project members") -> None:
        if role not in ("ADMIN", "OWNER"):
            raise UnauthorizedError(f"You must be a workspace Admin or Owner to {action}.")

    async def add_member(self, payload: AddMemberPayload) -> ProjectMember:
        """Add a user to a project.

        Raises:
            UnauthorizedError: If requester is not admin/owner.
            AlreadyProjectMemberError: If user already has active membership.
        """
        self._require_admin(payload.requesting_user_role)

        existing = await self._repo.get_active_membership(payload.project_id, payload.user_id)
        if existing:
            raise AlreadyProjectMemberError(
                f"User {payload.user_id} is already an active member of project {payload.project_id}."
            )

        return await self._repo.upsert_membership(
            project_id=payload.project_id,
            user_id=payload.user_id,
            assigned_by=payload.requesting_user_id,
            is_active=True,
        )

    async def remove_member(self, payload: RemoveMemberPayload) -> bool:
        """Deactivate a user's project membership.

        Returns True if removed, False if not found.
        Raises:
            UnauthorizedError: If requester is not admin/owner.
        """
        self._require_admin(payload.requesting_user_role)

        removed = await self._repo.deactivate_membership(payload.project_id, payload.user_id)
        return removed is not None

    async def list_members(self, payload: ListMembersPayload) -> ListMembersResult:
        """List project members with optional search and pagination."""
        page = await self._repo.list_members(
            project_id=payload.project_id,
            search=payload.search,
            is_active=payload.is_active,
            cursor=payload.cursor,
            page_size=payload.page_size,
        )
        return ListMembersResult(
            members=list(page.items),
            total=page.total,
            next_cursor=page.next_cursor,
            has_next=page.has_next,
        )

    async def bulk_update_assignments(self, payload: BulkUpdatePayload) -> BulkUpdateResult:
        """Bulk-add or bulk-remove project assignments for a workspace member.

        Also optionally updates workspace role (handled by caller updating the
        WorkspaceMember row; here we just record the intent and produce warnings).

        Returns a BulkUpdateResult with soft-warning messages for demotion.
        """
        self._require_admin(payload.requesting_user_role, "update project assignments")

        warnings: list[BulkUpdateWarning] = []
        updated = 0

        # Soft-warning for role demotion
        if payload.workspace_role:
            role_order = {"OWNER": 4, "ADMIN": 3, "MEMBER": 2, "GUEST": 1}
            current_rank = role_order.get(payload.current_workspace_role, 2)
            new_rank = role_order.get(payload.workspace_role, 2)
            if new_rank < current_rank:
                warnings.append(
                    BulkUpdateWarning(
                        code="role_demotion",
                        message=(
                            f"Demoting from {payload.current_workspace_role} to "
                            f"{payload.workspace_role}. The member will lose admin "
                            "capabilities."
                        ),
                    )
                )

        for item in payload.project_assignments:
            project_id = UUID(str(item["project_id"]))
            action = item["action"]
            if action == "add":
                await self._repo.upsert_membership(
                    project_id=project_id,
                    user_id=payload.target_user_id,
                    assigned_by=payload.requesting_user_id,
                    is_active=True,
                )
                updated += 1
            elif action == "remove":
                removed = await self._repo.deactivate_membership(project_id, payload.target_user_id)
                if removed:
                    updated += 1

        return BulkUpdateResult(
            user_id=payload.target_user_id,
            workspace_role=payload.workspace_role,
            project_assignments_updated=updated,
            warnings=warnings,
        )

    async def materialize_invite_assignments(self, payload: InviteAssignmentsPayload) -> int:
        """Create project_members rows from a workspace invitation's project_assignments.

        Called during invite acceptance (ensure_user_synced). Null-safe:
        if project_assignments is empty, does nothing.

        Returns number of memberships created.
        """
        if not payload.project_assignments:
            return 0

        created = 0
        for entry in payload.project_assignments:
            try:
                project_id = UUID(str(entry["project_id"]))
                # Use a SAVEPOINT per entry so that a DB-level failure (e.g. RLS
                # violation on project_members_insert) rolls back only this entry
                # and does NOT abort the outer PostgreSQL transaction.  Without a
                # savepoint, a swallowed exception leaves the transaction in the
                # ABORTED state, causing every subsequent RELEASE SAVEPOINT to
                # fail with InFailedSQLTransactionError.
                async with self._repo.session.begin_nested():
                    await self._repo.upsert_membership(
                        project_id=project_id,
                        user_id=payload.user_id,
                        assigned_by=payload.assigned_by,
                        is_active=True,
                    )
                created += 1
            except Exception:
                logger.exception(
                    "Failed to materialize project assignment for user %s, project %s",
                    payload.user_id,
                    entry.get("project_id"),
                )

        return created

    async def update_last_active_project(
        self,
        workspace_id: UUID,
        user_id: UUID,
        project_id: UUID | None,
    ) -> None:
        """Update workspace_member.last_active_project_id (non-blocking intent).

        Actual DB update is performed by the caller after retrieving the
        WorkspaceMember row; this method validates membership when project_id
        is provided.

        Raises:
            NotProjectMemberError: If user is not an active member of the project.
        """
        if project_id is None:
            return

        active_membership = await self._repo.get_active_membership(project_id, user_id)
        if not active_membership:
            raise NotProjectMemberError(
                f"User {user_id} is not an active member of project {project_id}."
            )
