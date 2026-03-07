"""Test scaffolds for RBACService — AUTH-05.

These tests define the expected contract for the custom RBAC service before
implementation begins. All tests are marked xfail(strict=False) so they
are collected by pytest and run, but do not block the suite.

Requirements covered:
  AUTH-05: Workspace-defined custom roles with granular permission sets
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# AUTH-05: Custom role CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="RBACService.create_custom_role not yet implemented (AUTH-05)",
)
async def test_custom_role_created_with_permissions() -> None:
    """A custom role is persisted with the provided permission list.

    Scenario:
        Given a workspace admin calls RBACService.create_custom_role(
            workspace_id, name="reviewer", permissions=["issues:read", "notes:read"]
        )
        When the role is retrieved by ID
        Then role.name == "reviewer"
        And role.permissions == ["issues:read", "notes:read"]
        And role.workspace_id matches the workspace
    """
    raise NotImplementedError("AUTH-05: RBACService.create_custom_role not implemented")


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="RBACService.check_permission not yet implemented (AUTH-05)",
)
async def test_check_permission_returns_true_for_allowed() -> None:
    """check_permission returns True when member's custom role has the permission.

    Scenario:
        Given member has custom_role with permissions=["issues:write"]
        When RBACService.check_permission(member_id, "issues:write") is called
        Then the result is True
    """
    raise NotImplementedError("AUTH-05: RBACService.check_permission not implemented")


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="RBACService.check_permission denial not yet implemented (AUTH-05)",
)
async def test_check_permission_returns_false_for_denied() -> None:
    """check_permission returns False when the permission is not in the role's list.

    Scenario:
        Given member has custom_role with permissions=["issues:read"]
        When RBACService.check_permission(member_id, "issues:write") is called
        Then the result is False
    """
    raise NotImplementedError("AUTH-05: RBACService.check_permission denial not implemented")


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="RBACService built-in role fallback not yet implemented (AUTH-05)",
)
async def test_member_without_custom_role_falls_back_to_builtin() -> None:
    """Members without a custom role fall back to built-in role permissions.

    Scenario:
        Given member has custom_role_id = None and role = MEMBER
        When RBACService.check_permission(member_id, "issues:write") is called
        Then the result uses built-in MEMBER permission matrix
        And no AttributeError or NoneType error is raised
    """
    raise NotImplementedError(
        "AUTH-05: Built-in role fallback for members without custom role not implemented"
    )


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="RBACService unique name constraint not yet implemented (AUTH-05)",
)
async def test_custom_role_name_unique_per_workspace() -> None:
    """Creating two custom roles with the same name in a workspace raises an error.

    Scenario:
        Given workspace already has a custom role named "reviewer"
        When RBACService.create_custom_role(workspace_id, name="reviewer", ...) is called
        Then a DuplicateRoleError (or similar domain error) is raised
        And only one role with name "reviewer" exists in the workspace
    """
    raise NotImplementedError("AUTH-05: Unique custom role name enforcement not implemented")
