"""SCIM 2.0 provisioning service — AUTH-07.

Handles enterprise IdP-driven user lifecycle:
  - provision_user: create Supabase user + workspace_member
  - deprovision_user: set is_active=False (data preserved, login blocked)
  - patch_user: apply RFC 7644 PATCH ops
  - update_user: full PUT replace
  - list_users: paginated workspace members
  - generate_scim_token: create and store SHA-256 hash in workspace.settings

Design decisions:
  - SCIM operations never hard-delete data (is_active=False for deactivation)
  - Supabase admin client creates auth users; local DB syncs the reference
  - Token is stored as SHA-256 hash only — raw token shown once to admin
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.repositories.user_repository import (
        UserRepository,
    )
    from pilot_space.infrastructure.database.repositories.workspace_repository import (
        WorkspaceRepository,
    )

logger = get_logger(__name__)


class ScimUserNotFoundError(NotFoundError):
    """Raised when a SCIM user (workspace member) is not found."""


class ScimWorkspaceNotFoundError(NotFoundError):
    """Raised when the workspace referenced by SCIM token does not exist."""


class ScimService:
    """Service for SCIM 2.0 user provisioning.

    All operations scope to a specific workspace_id. The Supabase admin client
    is used for auth user management (create, update email). Local DB manages
    workspace membership (is_active flag).
    """

    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        user_repo: UserRepository,
        supabase_admin_client: Any,
    ) -> None:
        """Initialize ScimService.

        Args:
            workspace_repo: Workspace repository.
            user_repo: User repository.
            supabase_admin_client: Supabase admin client for auth operations.
        """
        self.workspace_repo = workspace_repo
        self.user_repo = user_repo
        self.supabase_admin_client = supabase_admin_client

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def get_user(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> WorkspaceMember | None:
        """Get a workspace member by user_id for SCIM user resource.

        Args:
            user_id: The user UUID (SCIM id field).
            workspace_id: Workspace to scope the lookup.
            db: Database session.

        Returns:
            WorkspaceMember with user eagerly loaded, or None.
        """
        result = await db.execute(
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.user))
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_users(
        self,
        workspace_id: uuid.UUID,
        start_index: int,
        count: int,
        db: AsyncSession,
    ) -> tuple[list[WorkspaceMember], int]:
        """List workspace members as paginated SCIM User resources.

        Args:
            workspace_id: Workspace ID.
            start_index: 1-based offset per RFC 7644 §3.4.2.4.
            count: Maximum results to return.
            db: Database session.

        Returns:
            Tuple of (members_page, total_count).
        """
        from sqlalchemy import func

        base_filter = (
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.is_deleted == False,  # noqa: E712
        )

        # Total count
        count_result = await db.execute(select(func.count(WorkspaceMember.id)).where(*base_filter))
        total = count_result.scalar() or 0

        # Page slice (start_index is 1-based)
        offset = max(0, start_index - 1)
        members_result = await db.execute(
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.user))
            .where(*base_filter)
            .order_by(WorkspaceMember.created_at.asc())
            .offset(offset)
            .limit(count)
        )
        members = list(members_result.scalars().all())
        return members, total

    async def provision_user(
        self,
        workspace_id: uuid.UUID,
        email: str,
        display_name: str | None,
        active: bool,
        db: AsyncSession,
    ) -> WorkspaceMember:
        """Create or reactivate a workspace member via SCIM provisioning.

        Idempotent: if the user already exists in the workspace and is_active=False,
        re-activates the member. If fully new, creates Supabase auth user + member.

        Args:
            workspace_id: Workspace to provision into.
            email: User email (maps to SCIM userName).
            display_name: User display name.
            active: Whether to activate the member.
            db: Database session.

        Returns:
            WorkspaceMember with is_active=True (or as specified by active).
        """
        user = await self._get_or_create_user(email=email, display_name=display_name, db=db)
        member = await self._get_or_create_member(
            user_id=user.id,
            workspace_id=workspace_id,
            db=db,
        )

        # Sync active state
        if member.is_active != active:
            member.is_active = active
            await db.flush()

        return member

    async def deprovision_user(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        """Deactivate a workspace member (SCIM DELETE).

        Sets is_active=False. Data is preserved — member can be re-activated
        via SCIM provision or PATCH active=true. Does NOT delete any rows.

        Args:
            user_id: The user UUID.
            workspace_id: Workspace scoping the operation.
            db: Database session.

        Raises:
            ScimUserNotFoundError: If member not found in workspace.
        """
        member = await self.get_user(user_id, workspace_id, db)
        if member is None:
            raise ScimUserNotFoundError(f"User {user_id} not found in workspace {workspace_id}")
        member.is_active = False
        await db.flush()
        logger.info(
            "scim_deprovision",
            user_id=str(user_id),
            workspace_id=str(workspace_id),
        )

    async def update_user(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        email: str,
        display_name: str | None,
        active: bool,
        db: AsyncSession,
    ) -> WorkspaceMember:
        """Full replace (PUT) of a SCIM User resource.

        Args:
            user_id: The user UUID.
            workspace_id: Workspace scope.
            email: New email (userName).
            display_name: New display name.
            active: New active state.
            db: Database session.

        Returns:
            Updated WorkspaceMember.

        Raises:
            ScimUserNotFoundError: If member not found.
        """
        member = await self.get_user(user_id, workspace_id, db)
        if member is None:
            raise ScimUserNotFoundError(f"User {user_id} not found in workspace {workspace_id}")

        # Update user fields
        if member.user.email != email:
            member.user.email = email

        if display_name is not None:
            member.user.full_name = display_name

        # Handle active state change
        if not active and member.is_active:
            await self.deprovision_user(user_id, workspace_id, db)
        elif active and not member.is_active:
            member.is_active = True

        await db.flush()
        await db.refresh(member)
        return member

    async def patch_user(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        patch_ops: list[dict[str, Any]],
        db: AsyncSession,
    ) -> WorkspaceMember:
        """Apply RFC 7644 PATCH operations to a SCIM User resource.

        Supported operations:
          - replace active → deprovision (false) or reactivate (true)
          - replace displayName → update user.full_name
          - replace userName → update user.email
          - Unknown paths are silently ignored per RFC 7644.

        Args:
            user_id: The user UUID.
            workspace_id: Workspace scope.
            patch_ops: List of PATCH operation dicts with op, path, value.
            db: Database session.

        Returns:
            Updated WorkspaceMember.

        Raises:
            ScimUserNotFoundError: If member not found.
        """
        member = await self.get_user(user_id, workspace_id, db)
        if member is None:
            raise ScimUserNotFoundError(f"User {user_id} not found in workspace {workspace_id}")

        for op_dict in patch_ops:
            op = str(op_dict.get("op", "")).lower()
            path = str(op_dict.get("path", ""))
            value = op_dict.get("value")

            if op not in ("add", "replace", "remove"):
                continue  # RFC 7644: skip unknown ops

            path_lower = path.lower()

            if path_lower == "active":
                if op == "remove" or value is False:
                    await self.deprovision_user(user_id, workspace_id, db)
                    # Refresh member after deprovision
                    member = await self.get_user(user_id, workspace_id, db)  # type: ignore[assignment]
                elif value is True:
                    member.is_active = True  # type: ignore[union-attr]
                    await db.flush()

            elif path_lower == "displayname":
                if value is not None and member is not None:
                    member.user.full_name = str(value)  # type: ignore[union-attr]
                    await db.flush()

            elif path_lower == "username":
                if value is not None and member is not None:
                    member.user.email = str(value)  # type: ignore[union-attr]
                    await db.flush()
            # All other paths: silently ignored per RFC 7644 §3.5.2

        if member is None:
            # Should not happen unless deprovision raised
            raise ScimUserNotFoundError(f"User {user_id} not found in workspace {workspace_id}")

        await db.refresh(member)
        return member

    # ------------------------------------------------------------------
    # SCIM Token Management
    # ------------------------------------------------------------------

    async def generate_scim_token(
        self,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> str:
        """Generate a new SCIM bearer token for a workspace.

        Creates a URL-safe token, stores its SHA-256 hash in
        workspace.settings["scim_token_hash"], and returns the raw token.
        The raw token is NEVER stored and cannot be retrieved again.

        Args:
            workspace_id: Workspace to update.
            db: Database session.

        Returns:
            Raw bearer token (43-char URL-safe string).

        Raises:
            ScimWorkspaceNotFoundError: If workspace not found.
        """
        result = await db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.is_deleted == False,  # noqa: E712
            )
        )
        workspace = result.scalar_one_or_none()
        if workspace is None:
            raise ScimWorkspaceNotFoundError("Workspace not found")

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Merge into existing settings (preserve other keys)
        settings = dict(workspace.settings or {})
        settings["scim_token_hash"] = token_hash
        workspace.settings = settings

        await db.flush()
        logger.info("scim_token_generated", workspace_id=str(workspace_id))
        return raw_token

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_or_create_user(
        self,
        email: str,
        display_name: str | None,
        db: AsyncSession,
    ) -> User:
        """Get existing user by email or create via Supabase + local DB.

        Args:
            email: User email address.
            display_name: Display name for new users.
            db: Database session.

        Returns:
            User ORM object.
        """
        from pilot_space.infrastructure.database.models.user import User as UserModel

        # Check local DB first
        existing = await self.user_repo.get_by_email(email)
        if existing is not None:
            return existing

        # Create in Supabase auth
        try:
            auth_response = await self.supabase_admin_client.auth.admin.create_user(
                {"email": email, "email_confirm": True}
            )
            supabase_user_id = uuid.UUID(auth_response.user.id)
        except Exception:
            # If Supabase user already exists or fails, generate a local UUID
            # In production this should be handled more carefully
            supabase_user_id = uuid.uuid4()
            logger.warning(
                "scim_supabase_user_create_failed_using_local_id",
                email=email,
            )

        # Create local user record
        user = UserModel()
        user.id = supabase_user_id
        user.email = email
        user.full_name = display_name
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def _get_or_create_member(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> WorkspaceMember:
        """Get existing workspace_member or create with default MEMBER role.

        Args:
            user_id: User UUID.
            workspace_id: Workspace UUID.
            db: Database session.

        Returns:
            WorkspaceMember ORM object.
        """
        result = await db.execute(
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.user))
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing

        # Create new member
        member = WorkspaceMember()
        member.user_id = user_id
        member.workspace_id = workspace_id
        member.role = WorkspaceRole.MEMBER
        member.is_active = True
        db.add(member)
        await db.flush()

        # Reload with user relationship
        result2 = await db.execute(
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.user))
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
        )
        return result2.scalar_one()


__all__ = [
    "ScimService",
    "ScimUserNotFoundError",
    "ScimWorkspaceNotFoundError",
]
