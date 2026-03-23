"""Workspace feature toggle service.

Manages per-workspace sidebar feature visibility (notes, issues, projects, etc.).
Admin/owner can update toggles; any workspace member can read them.

Error hierarchy follows the TranscriptionError pattern (error_code + http_status)
so the global exception handler in error_handler.py converts these to RFC 7807
application/problem+json responses automatically.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from pilot_space.api.v1.schemas.workspace import (
    WorkspaceFeatureToggles,
    WorkspaceFeatureTogglesUpdate,
)
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

SETTINGS_KEY = "feature_toggles"


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class FeatureToggleError(Exception):
    """Base error for feature toggle failures.

    Follows the TranscriptionError pattern (error_code + http_status) so the
    global exception handler converts these to RFC 7807 responses.
    """

    error_code: str = "feature_toggle_error"
    http_status: int = 500

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.error_code = code


class WorkspaceNotFoundError(FeatureToggleError):
    """Workspace does not exist."""

    error_code = "workspace_not_found"
    http_status = 404


class NotAMemberError(FeatureToggleError):
    """User is not a member of the workspace.

    SEC-M1: returns 404 (not 403) to prevent workspace-ID enumeration.
    """

    error_code = "not_a_member"
    http_status = 404


class InsufficientPermissionError(FeatureToggleError):
    """User does not have admin/owner role.

    SEC-M1: returns 404 (not 403) to prevent workspace-ID enumeration.
    """

    error_code = "insufficient_permission"
    http_status = 404


class EmptyUpdateError(FeatureToggleError):
    """Update body contains no fields to change."""

    error_code = "empty_update"
    http_status = 422


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


def _extract_toggles(workspace: Workspace) -> WorkspaceFeatureToggles:
    """Extract feature toggles from workspace settings, falling back to defaults."""
    if not workspace.settings or SETTINGS_KEY not in workspace.settings:
        return WorkspaceFeatureToggles()

    toggles_data = workspace.settings[SETTINGS_KEY]
    return WorkspaceFeatureToggles(**toggles_data)


class FeatureToggleService:
    """Service for reading and updating workspace feature toggles.

    Encapsulates workspace lookup, membership/role checks, and settings
    persistence.  Raises FeatureToggleError subclasses on failure so the
    router stays thin and the global handler converts to RFC 7807.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkspaceRepository(session=session)

    # -- helpers ----------------------------------------------------------

    async def _require_workspace(self, workspace_id: UUID) -> Workspace:
        """Look up workspace or raise WorkspaceNotFoundError."""
        workspace = await self._repo.get_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")
        return workspace

    async def _require_member(self, workspace_id: UUID, user_id: UUID) -> Workspace:
        """Require the user to be a workspace member (any role).

        SEC-M1: raises NotAMemberError(404) with generic message to prevent
        workspace-ID enumeration.
        """
        workspace = await self._require_workspace(workspace_id)
        if not await self._repo.is_member(workspace_id, user_id):
            raise NotAMemberError("Workspace not found")
        return workspace

    async def _require_admin(self, workspace_id: UUID, user_id: UUID) -> Workspace:
        """Require the user to be a workspace admin or owner.

        SEC-M1: raises InsufficientPermissionError(404) with generic message
        to prevent workspace-ID enumeration.
        """
        from pilot_space.infrastructure.database.models.workspace_member import (
            WorkspaceRole,
        )

        workspace = await self._require_workspace(workspace_id)
        role = await self._repo.get_member_role(workspace_id, user_id)
        if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            raise InsufficientPermissionError("Workspace not found")
        return workspace

    # -- public API -------------------------------------------------------

    async def get_toggles(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceFeatureToggles:
        """Return current feature toggles for the workspace.

        Any authenticated workspace member may call this.

        Raises:
            WorkspaceNotFoundError: Workspace does not exist.
            NotAMemberError: User is not a member.
        """
        workspace = await self._require_member(workspace_id, user_id)
        return _extract_toggles(workspace)

    async def update_toggles(
        self,
        workspace_id: UUID,
        user_id: UUID,
        body: WorkspaceFeatureTogglesUpdate,
    ) -> WorkspaceFeatureToggles:
        """Partially update feature toggles.

        Only provided (non-None) fields are changed. Restricted to
        workspace owner or admin.

        Raises:
            WorkspaceNotFoundError: Workspace does not exist.
            InsufficientPermissionError: User is not admin/owner.
            EmptyUpdateError: No fields provided in the update body.
        """
        workspace = await self._require_admin(workspace_id, user_id)

        updates = body.model_dump(exclude_none=True)
        if not updates:
            raise EmptyUpdateError("At least one field must be provided.")

        workspace_settings = workspace.settings or {}
        existing_toggles = workspace_settings.get(SETTINGS_KEY, {})
        existing_toggles.update(updates)
        workspace_settings[SETTINGS_KEY] = existing_toggles

        workspace.settings = workspace_settings
        flag_modified(workspace, "settings")
        await self._repo.update(workspace)
        await self._session.commit()

        logger.info(
            "Feature toggles updated for workspace %s by user %s: %s",
            workspace_id,
            user_id,
            updates,
        )

        return _extract_toggles(workspace)
