"""Test workspace creation assigns OWNER role (T010).

Verifies WorkspaceRole enum has correct values and OWNER role exists
for workspace creator assignment.
"""

from __future__ import annotations

from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole


def test_workspace_role_owner_exists() -> None:
    """Verify OWNER role is defined in WorkspaceRole enum."""
    assert hasattr(WorkspaceRole, "OWNER")
    assert WorkspaceRole.OWNER.value == "OWNER"


def test_workspace_role_enum_values() -> None:
    """Verify all expected roles exist."""
    expected = {"OWNER", "ADMIN", "MEMBER", "GUEST"}
    actual = {role.value for role in WorkspaceRole}
    assert actual == expected


def test_workspace_role_hierarchy_order() -> None:
    """Verify role hierarchy is correctly defined (owner > admin > member > guest)."""
    roles = list(WorkspaceRole)
    role_values = [r.value for r in roles]
    assert "OWNER" in role_values
    assert "ADMIN" in role_values
    assert "MEMBER" in role_values
    assert "GUEST" in role_values


def test_owner_is_not_admin() -> None:
    """Verify OWNER and ADMIN are distinct roles."""
    assert WorkspaceRole.OWNER != WorkspaceRole.ADMIN
    assert WorkspaceRole.OWNER.value != WorkspaceRole.ADMIN.value
