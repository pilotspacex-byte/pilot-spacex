"""Permission definitions and check_permission helper for custom RBAC.

Defines:
  - RESOURCES: set of all known resource names
  - ACTIONS: set of all known action names
  - BUILTIN_ROLE_PERMISSIONS: capability map for the 4 built-in roles
  - check_permission(): async helper that resolves user permissions in a workspace

Permission format: "{resource}:{action}" e.g. "issues:write", "members:manage"

Built-in role hierarchy:
  owner  — all resources, all actions
  admin  — all resources except settings:manage (workspace deletion-level ops)
  member — issues R/W, notes R/W, cycles R, ai:read
  guest  — issues:read, notes:read
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import joinedload

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------

RESOURCES: frozenset[str] = frozenset(
    {"issues", "notes", "cycles", "members", "settings", "ai", "integrations"}
)

ACTIONS: frozenset[str] = frozenset({"read", "write", "delete", "manage"})

_ALL_PERMISSIONS: frozenset[str] = frozenset(f"{r}:{a}" for r in RESOURCES for a in ACTIONS)

# Admin can do everything except workspace-deletion-level settings management.
_ADMIN_EXCLUDED: frozenset[str] = frozenset({"settings:manage", "settings:delete"})

BUILTIN_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": _ALL_PERMISSIONS,
    "admin": _ALL_PERMISSIONS - _ADMIN_EXCLUDED,
    "member": frozenset(
        {
            "issues:read",
            "issues:write",
            "notes:read",
            "notes:write",
            "cycles:read",
            "cycles:write",
            "ai:read",
        }
    ),
    "guest": frozenset({"issues:read", "notes:read"}),
}


# ---------------------------------------------------------------------------
# Internal helper (tested via check_permission; injectable via patch in tests)
# ---------------------------------------------------------------------------


async def _get_member_with_role(
    session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
) -> object | None:
    """Load WorkspaceMember with custom_role eagerly loaded.

    Returns None if the user is not a member of the workspace.
    Uses a single query with joinedload to avoid N+1.
    """
    from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember

    stmt = (
        select(WorkspaceMember)
        .options(joinedload(WorkspaceMember.custom_role))
        .where(
            and_(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.is_deleted == False,  # noqa: E712
            )
        )
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def check_permission(
    session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
    resource: str,
    action: str,
) -> bool:
    """Check if user has resource:action permission in workspace.

    Checks custom_role first; falls back to built-in WorkspaceRole.
    Returns False when the user is not a member or is deactivated.

    Args:
        session: Async DB session (RLS context should be set by the caller).
        user_id: User whose permission is being checked.
        workspace_id: Workspace scope.
        resource: Resource name (must be in RESOURCES).
        action: Action name (must be in ACTIONS).

    Returns:
        True if the user has the specified permission, False otherwise.
    """
    member = await _get_member_with_role(session, user_id, workspace_id)
    if member is None or not member.is_active:  # type: ignore[union-attr]
        return False

    permission = f"{resource}:{action}"

    # Custom role takes precedence over built-in role
    if member.custom_role_id and member.custom_role:  # type: ignore[union-attr]
        return permission in (member.custom_role.permissions or [])  # type: ignore[union-attr]

    # Fall back to built-in role capability map
    # WorkspaceRole enum values are UPPERCASE in the model; normalize to lowercase key
    role_key = member.role.value.lower()  # type: ignore[union-attr]
    return permission in BUILTIN_ROLE_PERMISSIONS.get(role_key, frozenset())


__all__ = [
    "ACTIONS",
    "BUILTIN_ROLE_PERMISSIONS",
    "RESOURCES",
    "check_permission",
]
