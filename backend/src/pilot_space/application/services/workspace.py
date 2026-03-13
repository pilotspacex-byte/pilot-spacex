"""Workspace service for workspace CRUD and member invitation logic.

Handles workspace operations following CQRS-lite pattern (DD-064):
- Workspace CRUD (list, get, create, update, delete)
- Member invitation (existing users added immediately, new users get pending invitation)
- Label management

Source: FR-014, FR-015, FR-016, US3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
    WorkspaceInvitation,
)
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.label import Label
    from pilot_space.infrastructure.database.repositories.invitation_repository import (
        InvitationRepository,
    )
    from pilot_space.infrastructure.database.repositories.label_repository import (
        LabelRepository,
    )
    from pilot_space.infrastructure.database.repositories.user_repository import (
        UserRepository,
    )
    from pilot_space.infrastructure.database.repositories.workspace_repository import (
        WorkspaceRepository,
    )

logger = get_logger(__name__)


# ===== Payloads & Results =====


@dataclass
class ListWorkspacesPayload:
    """Payload for listing user workspaces."""

    user_id: UUID
    cursor: str | None = None
    page_size: int = 20


@dataclass
class ListWorkspacesResult:
    """Result of list_workspaces operation."""

    workspaces: list[Workspace]
    total: int
    next_cursor: str | None
    prev_cursor: str | None
    has_next: bool
    has_prev: bool


@dataclass
class GetWorkspacePayload:
    """Payload for getting workspace by ID or slug."""

    workspace_id_or_slug: str  # UUID or slug
    user_id: UUID


@dataclass
class GetWorkspaceResult:
    """Result of get_workspace operation."""

    workspace: Workspace
    current_user_role: str
    member_count: int
    project_count: int


@dataclass
class CreateWorkspacePayload:
    """Payload for creating workspace."""

    name: str
    slug: str
    description: str | None
    owner_id: UUID


@dataclass
class CreateWorkspaceResult:
    """Result of create_workspace operation."""

    workspace: Workspace
    owner_member: WorkspaceMember


@dataclass
class UpdateWorkspacePayload:
    """Payload for updating workspace."""

    workspace_id_or_slug: str
    user_id: UUID
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    settings: dict[str, Any] | None = None


@dataclass
class UpdateWorkspaceResult:
    """Result of update_workspace operation."""

    workspace: Workspace
    changed_fields: list[str] = field(default_factory=list)


@dataclass
class DeleteWorkspacePayload:
    """Payload for soft-deleting workspace."""

    workspace_id_or_slug: str
    user_id: UUID


@dataclass
class DeleteWorkspaceResult:
    """Result of delete_workspace operation."""

    workspace_id: UUID
    deleted_at: datetime


@dataclass
class ListLabelsPayload:
    """Payload for listing workspace labels."""

    workspace_id_or_slug: str
    user_id: UUID
    project_id: UUID | None = None


@dataclass
class ListLabelsResult:
    """Result of list_labels operation."""

    labels: list[Label]


@dataclass
class InviteMemberResult:
    """Result of invite_member operation.

    Attributes:
        is_immediate: True if user was added immediately (existing user).
        member: WorkspaceMember if immediate add.
        invitation: WorkspaceInvitation if pending invitation created.
    """

    is_immediate: bool
    member: WorkspaceMember | None = None
    invitation: WorkspaceInvitation | None = None


class WorkspaceService:
    """Service for workspace CRUD and member invitation operations.

    Follows CQRS-lite pattern per DD-064.
    """

    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        user_repo: UserRepository,
        invitation_repo: InvitationRepository,
        label_repo: LabelRepository,
    ) -> None:
        self.workspace_repo = workspace_repo
        self.user_repo = user_repo
        self.invitation_repo = invitation_repo
        self.label_repo = label_repo

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        """Check if string is valid UUID."""
        try:
            UUID(value)
            return True
        except ValueError:
            return False

    async def _resolve_workspace(
        self,
        id_or_slug: str,
        *,
        load_members: bool = True,
    ) -> Workspace:
        """Resolve workspace by UUID or slug.

        Args:
            id_or_slug: Workspace ID (UUID) or slug.
            load_members: If True, eagerly load members relationship.

        Returns:
            Workspace entity.

        Raises:
            ValueError: If workspace not found.
        """
        if self._is_valid_uuid(id_or_slug):
            if load_members:
                workspace = await self.workspace_repo.get_with_members(UUID(id_or_slug))
            else:
                workspace = await self.workspace_repo.get_by_id(UUID(id_or_slug))
        elif load_members:
            workspace = await self.workspace_repo.get_by_slug_with_members(id_or_slug)
        else:
            workspace = await self.workspace_repo.get_by_slug(id_or_slug)

        if not workspace:
            msg = "Workspace not found"
            raise ValueError(msg)

        return workspace

    async def list_workspaces(
        self,
        payload: ListWorkspacesPayload,
    ) -> ListWorkspacesResult:
        """List workspaces user is member of.

        Args:
            payload: List workspaces payload.

        Returns:
            Paginated workspace list.
        """
        workspaces = await self.workspace_repo.get_user_workspaces(
            user_id=payload.user_id
        )

        # Apply simple pagination
        total = len(workspaces)
        start_idx = 0
        if payload.cursor and payload.cursor.isdigit():
            start_idx = int(payload.cursor)
        end_idx = start_idx + payload.page_size
        paginated = workspaces[start_idx:end_idx]
        has_next = end_idx < total
        has_prev = start_idx > 0

        return ListWorkspacesResult(
            workspaces=list(paginated),
            total=total,
            next_cursor=str(end_idx) if has_next else None,
            prev_cursor=(
                str(max(0, start_idx - payload.page_size)) if has_prev else None
            ),
            has_next=has_next,
            has_prev=has_prev,
        )

    async def get_workspace(
        self,
        payload: GetWorkspacePayload,
    ) -> GetWorkspaceResult:
        """Get workspace by ID or slug with membership check.

        Args:
            payload: Get workspace payload.

        Returns:
            Workspace with member info.

        Raises:
            ValueError: If workspace not found or user not member.
        """
        workspace = await self._resolve_workspace(
            payload.workspace_id_or_slug,
            load_members=True,
        )

        # Check membership
        member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.user_id),
            None,
        )
        if not member:
            msg = "Not a member of this workspace"
            raise ValueError(msg)

        return GetWorkspaceResult(
            workspace=workspace,
            current_user_role=member.role.value,
            member_count=len(workspace.members) if workspace.members else 0,
            project_count=len(workspace.projects) if workspace.projects else 0,
        )

    async def create_workspace(
        self,
        payload: CreateWorkspacePayload,
    ) -> CreateWorkspaceResult:
        """Create new workspace and add creator as owner.

        Args:
            payload: Create workspace payload.

        Returns:
            Created workspace with owner membership.

        Raises:
            ValueError: If slug already exists.
        """
        # Check slug uniqueness
        existing = await self.workspace_repo.get_by_slug(payload.slug)
        if existing:
            msg = f"Workspace with slug '{payload.slug}' already exists"
            raise ValueError(msg)

        # Create workspace
        workspace = Workspace(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            owner_id=payload.owner_id,
        )
        workspace = await self.workspace_repo.create(workspace)

        # Add creator as owner (FR-007)
        owner_member = await self.workspace_repo.add_member(
            workspace_id=workspace.id,
            user_id=payload.owner_id,
            role=WorkspaceRole.OWNER,
        )

        logger.info(
            "Workspace created",
            extra={"workspace_id": str(workspace.id), "slug": workspace.slug},
        )

        return CreateWorkspaceResult(
            workspace=workspace,
            owner_member=owner_member,
        )

    async def update_workspace(
        self,
        payload: UpdateWorkspacePayload,
    ) -> UpdateWorkspaceResult:
        """Update workspace (name, description, settings).

        Requires admin role.

        Args:
            payload: Update workspace payload.

        Returns:
            Updated workspace with changed fields.

        Raises:
            ValueError: If workspace not found or user not admin.
        """
        workspace = await self._resolve_workspace(
            payload.workspace_id_or_slug,
            load_members=True,
        )

        # Check admin role
        member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.user_id),
            None,
        )
        if not member or not member.is_admin:
            msg = "Admin role required"
            raise ValueError(msg)

        # Track changed fields
        changed_fields: list[str] = []

        # Update fields
        if payload.name is not None:
            workspace.name = payload.name
            changed_fields.append("name")
        if payload.slug is not None and payload.slug != workspace.slug:
            slug_taken = await self.workspace_repo.slug_exists(
                payload.slug, exclude_id=workspace.id
            )
            if slug_taken:
                msg = f"Slug '{payload.slug}' is already taken"
                raise ValueError(msg)
            workspace.slug = payload.slug
            changed_fields.append("slug")
        if payload.description is not None:
            workspace.description = payload.description
            changed_fields.append("description")
        if payload.settings is not None:
            # M-2 fix: merge settings dict instead of replacing
            existing_settings = workspace.settings or {}
            existing_settings.update(payload.settings)
            workspace.settings = existing_settings
            changed_fields.append("settings")

        if changed_fields:
            workspace = await self.workspace_repo.update(workspace)

        logger.info(
            "Workspace updated",
            extra={
                "workspace_id": str(workspace.id),
                "changed_fields": changed_fields,
            },
        )

        return UpdateWorkspaceResult(
            workspace=workspace,
            changed_fields=changed_fields,
        )

    async def delete_workspace(
        self,
        payload: DeleteWorkspacePayload,
    ) -> DeleteWorkspaceResult:
        """Soft delete workspace.

        Requires owner role.

        Args:
            payload: Delete workspace payload.

        Returns:
            Deleted workspace ID and timestamp.

        Raises:
            ValueError: If workspace not found or user not owner.
        """
        workspace = await self._resolve_workspace(
            payload.workspace_id_or_slug,
            load_members=True,
        )

        # H-6 fix: workspace deletion is destructive — requires owner role
        member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.user_id),
            None,
        )
        if not member or not member.is_owner:
            msg = "Owner role required to delete workspace"
            raise ValueError(msg)

        await self.workspace_repo.delete(workspace)

        logger.info(
            "Workspace deleted",
            extra={"workspace_id": str(workspace.id)},
        )

        return DeleteWorkspaceResult(
            workspace_id=workspace.id,
            deleted_at=datetime.now(tz=UTC),
        )

    async def list_labels(
        self,
        payload: ListLabelsPayload,
    ) -> ListLabelsResult:
        """List labels available in workspace.

        Args:
            payload: List labels payload.

        Returns:
            List of labels (workspace-wide and optionally project-specific).

        Raises:
            ValueError: If workspace not found or user not member.
        """
        workspace = await self._resolve_workspace(
            payload.workspace_id_or_slug,
            load_members=True,
        )

        # Check membership
        is_member = any(m.user_id == payload.user_id for m in (workspace.members or []))
        if not is_member:
            msg = "Not a member of this workspace"
            raise ValueError(msg)

        labels = await self.label_repo.get_workspace_labels(
            workspace.id,
            include_project_labels=True,
            project_id=payload.project_id,
        )

        return ListLabelsResult(labels=list(labels))

    async def invite_member(
        self,
        workspace_id: UUID,
        email: str,
        role: str,
        invited_by: UUID,
    ) -> InviteMemberResult:
        """Invite a member to a workspace.

        If the email belongs to an existing user, add them immediately.
        If not, create a pending invitation for auto-accept on signup.

        Args:
            workspace_id: Target workspace UUID.
            email: Email address to invite.
            role: Intended role (admin, member, guest).
            invited_by: UUID of the admin sending the invite.

        Returns:
            InviteMemberResult with either member or invitation.

        Raises:
            ValueError: If user is already a member or has pending invitation.
        """
        normalized_email = email.strip().lower()
        workspace_role = WorkspaceRole(role)

        # Check if user exists in the system
        existing_user = await self.user_repo.get_by_email(normalized_email)

        if existing_user:
            # Check if already a member
            is_member = await self.workspace_repo.is_member(
                workspace_id, existing_user.id
            )
            if is_member:
                msg = "User is already a member of this workspace"
                raise ValueError(msg)

            # Add immediately
            member = await self.workspace_repo.add_member(
                workspace_id=workspace_id,
                user_id=existing_user.id,
                role=workspace_role,
            )

            logger.info(
                "Member added immediately",
                extra={
                    "workspace_id": str(workspace_id),
                    "user_id": str(existing_user.id),
                    "role": role,
                },
            )

            return InviteMemberResult(is_immediate=True, member=member)

        # User doesn't exist — check for duplicate pending invitation
        has_pending = await self.invitation_repo.exists_pending(
            workspace_id, normalized_email
        )
        if has_pending:
            msg = "An invitation is already pending for this email"
            raise ValueError(msg)

        # Create pending invitation
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=normalized_email,
            role=workspace_role,
            invited_by=invited_by,
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(tz=UTC) + timedelta(days=7),
        )
        invitation = await self.invitation_repo.create(invitation)

        logger.info(
            "Invitation created",
            extra={
                "workspace_id": str(workspace_id),
                "email": normalized_email,
                "role": role,
                "invitation_id": str(invitation.id),
            },
        )

        return InviteMemberResult(is_immediate=False, invitation=invitation)
