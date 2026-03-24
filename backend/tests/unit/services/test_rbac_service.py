"""Unit tests for RbacService and check_permission — AUTH-05.

Tests cover:
  - check_permission: custom role allowed/denied, built-in role fallback
  - BUILTIN_ROLE_PERMISSIONS: owner all, guest read-only, member subset
  - RbacService.create_role: validation, duplicate name detection
  - RbacService.assign_role_to_member: set/clear custom_role_id
  - RbacService.delete_role: member assignment clearing
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.application.services.rbac_service import (
    DuplicateRoleNameError,
    MemberNotFoundError,
    RbacService,
)
from pilot_space.domain.exceptions import ValidationError
from pilot_space.infrastructure.database.permissions import (
    BUILTIN_ROLE_PERMISSIONS,
    check_permission,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_member(
    *,
    role: str = "MEMBER",
    is_active: bool = True,
    custom_role_id: uuid.UUID | None = None,
    custom_role_permissions: list[str] | None = None,
) -> MagicMock:
    """Build a WorkspaceMember-like MagicMock."""
    member = MagicMock()
    member.is_active = is_active
    member.custom_role_id = custom_role_id
    member.role = MagicMock()
    member.role.value = role  # e.g. "OWNER", "MEMBER", "GUEST"

    if custom_role_id is not None:
        member.custom_role_id = custom_role_id
        if custom_role_permissions is not None:
            member.custom_role = MagicMock()
            member.custom_role.permissions = custom_role_permissions
        else:
            member.custom_role = None
    else:
        member.custom_role = None
        member.custom_role_id = None

    return member


def _make_custom_role(
    *,
    role_id: uuid.UUID | None = None,
    name: str = "reviewer",
    workspace_id: uuid.UUID | None = None,
    permissions: list[str] | None = None,
) -> MagicMock:
    """Build a CustomRole-like MagicMock."""
    role = MagicMock()
    role.id = role_id or uuid.uuid4()
    role.name = name
    role.workspace_id = workspace_id or uuid.uuid4()
    role.permissions = permissions or ["issues:read"]
    role.description = None
    return role


# ---------------------------------------------------------------------------
# check_permission — custom role path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_permission_custom_role_allowed() -> None:
    """check_permission returns True when custom role has the permission."""
    role_id = uuid.uuid4()
    member = _make_member(
        custom_role_id=role_id,
        custom_role_permissions=["issues:write", "notes:read"],
    )
    session = MagicMock()

    with patch(
        "pilot_space.infrastructure.database.permissions._get_member_with_role",
        new=AsyncMock(return_value=member),
    ):
        result = await check_permission(session, uuid.uuid4(), uuid.uuid4(), "issues", "write")

    assert result is True


@pytest.mark.asyncio
async def test_check_permission_custom_role_denied() -> None:
    """check_permission returns False when custom role lacks the permission."""
    role_id = uuid.uuid4()
    member = _make_member(
        custom_role_id=role_id,
        custom_role_permissions=["issues:read"],
    )
    session = MagicMock()

    with patch(
        "pilot_space.infrastructure.database.permissions._get_member_with_role",
        new=AsyncMock(return_value=member),
    ):
        result = await check_permission(session, uuid.uuid4(), uuid.uuid4(), "issues", "write")

    assert result is False


# ---------------------------------------------------------------------------
# check_permission — built-in role fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_permission_builtin_owner_all() -> None:
    """Built-in OWNER role is granted every permission."""
    member = _make_member(role="OWNER")
    session = MagicMock()

    with patch(
        "pilot_space.infrastructure.database.permissions._get_member_with_role",
        new=AsyncMock(return_value=member),
    ):
        result = await check_permission(session, uuid.uuid4(), uuid.uuid4(), "settings", "manage")

    assert result is True


@pytest.mark.asyncio
async def test_check_permission_builtin_guest_cannot_write() -> None:
    """Built-in GUEST role cannot write issues."""
    member = _make_member(role="GUEST")
    session = MagicMock()

    with patch(
        "pilot_space.infrastructure.database.permissions._get_member_with_role",
        new=AsyncMock(return_value=member),
    ):
        result = await check_permission(session, uuid.uuid4(), uuid.uuid4(), "issues", "write")

    assert result is False


@pytest.mark.asyncio
async def test_check_permission_inactive_member_denied() -> None:
    """Inactive member is always denied regardless of role."""
    member = _make_member(role="OWNER", is_active=False)
    session = MagicMock()

    with patch(
        "pilot_space.infrastructure.database.permissions._get_member_with_role",
        new=AsyncMock(return_value=member),
    ):
        result = await check_permission(session, uuid.uuid4(), uuid.uuid4(), "issues", "read")

    assert result is False


@pytest.mark.asyncio
async def test_check_permission_nonmember_denied() -> None:
    """Non-member (None) is always denied."""
    session = MagicMock()

    with patch(
        "pilot_space.infrastructure.database.permissions._get_member_with_role",
        new=AsyncMock(return_value=None),
    ):
        result = await check_permission(session, uuid.uuid4(), uuid.uuid4(), "issues", "read")

    assert result is False


# ---------------------------------------------------------------------------
# BUILTIN_ROLE_PERMISSIONS correctness
# ---------------------------------------------------------------------------


def test_builtin_owner_has_all_permissions() -> None:
    """OWNER has every resource:action combination."""
    from pilot_space.infrastructure.database.permissions import ACTIONS, RESOURCES

    owner_perms = BUILTIN_ROLE_PERMISSIONS["owner"]
    for resource in RESOURCES:
        for action in ACTIONS:
            assert f"{resource}:{action}" in owner_perms, f"Owner missing {resource}:{action}"


def test_builtin_guest_readonly() -> None:
    """GUEST has only issues:read and notes:read."""
    guest_perms = BUILTIN_ROLE_PERMISSIONS["guest"]
    assert guest_perms == frozenset({"issues:read", "notes:read"})


def test_builtin_member_subset() -> None:
    """MEMBER has the expected permission subset."""
    member_perms = BUILTIN_ROLE_PERMISSIONS["member"]
    assert "issues:write" in member_perms
    assert "notes:write" in member_perms
    assert "ai:read" in member_perms
    # Not in member permissions
    assert "members:manage" not in member_perms
    assert "settings:manage" not in member_perms


# ---------------------------------------------------------------------------
# RbacService — create_role
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_role_with_valid_permissions() -> None:
    """create_role persists role and returns it."""
    workspace_id = uuid.uuid4()
    created_role = _make_custom_role(
        workspace_id=workspace_id,
        name="reviewer",
        permissions=["issues:read", "notes:read"],
    )

    custom_role_repo = MagicMock()
    custom_role_repo.get_by_name = AsyncMock(return_value=None)
    custom_role_repo.create = AsyncMock(return_value=created_role)

    member_repo = MagicMock()
    service = RbacService(custom_role_repo=custom_role_repo, workspace_member_repo=member_repo)

    result = await service.create_role(
        workspace_id=workspace_id,
        name="reviewer",
        description=None,
        permissions=["issues:read", "notes:read"],
        session=MagicMock(),
    )

    assert result.name == "reviewer"
    custom_role_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_role_raises_duplicate_name() -> None:
    """create_role raises DuplicateRoleNameError when name already exists."""
    workspace_id = uuid.uuid4()
    existing = _make_custom_role(workspace_id=workspace_id, name="reviewer")

    custom_role_repo = MagicMock()
    custom_role_repo.get_by_name = AsyncMock(return_value=existing)

    member_repo = MagicMock()
    service = RbacService(custom_role_repo=custom_role_repo, workspace_member_repo=member_repo)

    with pytest.raises(DuplicateRoleNameError):
        await service.create_role(
            workspace_id=workspace_id,
            name="reviewer",
            description=None,
            permissions=["issues:read"],
            session=MagicMock(),
        )


@pytest.mark.asyncio
async def test_create_role_raises_invalid_permission() -> None:
    """create_role raises ValidationError for unknown resource or action."""
    custom_role_repo = MagicMock()
    custom_role_repo.get_by_name = AsyncMock(return_value=None)

    member_repo = MagicMock()
    service = RbacService(custom_role_repo=custom_role_repo, workspace_member_repo=member_repo)

    with pytest.raises(ValidationError, match="invalid permission"):
        await service.create_role(
            workspace_id=uuid.uuid4(),
            name="bad",
            description=None,
            permissions=["unicorns:fly"],
            session=MagicMock(),
        )


# ---------------------------------------------------------------------------
# RbacService — assign_role_to_member
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_role_sets_custom_role_id() -> None:
    """assign_role_to_member sets member.custom_role_id."""
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    role_id = uuid.uuid4()

    member = _make_member(role="MEMBER")
    member.custom_role_id = None

    updated_member = _make_member(role="MEMBER", custom_role_id=role_id)

    member_repo = MagicMock()
    member_repo.get_by_user_workspace = AsyncMock(return_value=member)
    member_repo.update = AsyncMock(return_value=updated_member)

    custom_role_repo = MagicMock()
    service = RbacService(custom_role_repo=custom_role_repo, workspace_member_repo=member_repo)

    result = await service.assign_role_to_member(
        user_id=user_id,
        workspace_id=workspace_id,
        custom_role_id=role_id,
        session=MagicMock(),
    )

    assert result.custom_role_id == role_id
    member_repo.update.assert_called_once_with(member)


@pytest.mark.asyncio
async def test_assign_none_clears_custom_role() -> None:
    """assign_role_to_member with None clears the custom role."""
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()

    member = _make_member(role="MEMBER", custom_role_id=uuid.uuid4())
    cleared_member = _make_member(role="MEMBER")
    cleared_member.custom_role_id = None

    member_repo = MagicMock()
    member_repo.get_by_user_workspace = AsyncMock(return_value=member)
    member_repo.update = AsyncMock(return_value=cleared_member)

    custom_role_repo = MagicMock()
    service = RbacService(custom_role_repo=custom_role_repo, workspace_member_repo=member_repo)

    result = await service.assign_role_to_member(
        user_id=user_id,
        workspace_id=workspace_id,
        custom_role_id=None,
        session=MagicMock(),
    )

    assert result.custom_role_id is None


@pytest.mark.asyncio
async def test_assign_role_raises_for_nonmember() -> None:
    """assign_role_to_member raises MemberNotFoundError when user is not a member."""
    member_repo = MagicMock()
    member_repo.get_by_user_workspace = AsyncMock(return_value=None)

    custom_role_repo = MagicMock()
    service = RbacService(custom_role_repo=custom_role_repo, workspace_member_repo=member_repo)

    with pytest.raises(MemberNotFoundError):
        await service.assign_role_to_member(
            user_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            custom_role_id=uuid.uuid4(),
            session=MagicMock(),
        )


# ---------------------------------------------------------------------------
# RbacService — delete_role clears member assignments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_role_nullifies_member_assignments() -> None:
    """delete_role clears member custom_role assignments before soft-deleting."""
    workspace_id = uuid.uuid4()
    role_id = uuid.uuid4()
    role = _make_custom_role(role_id=role_id, workspace_id=workspace_id)

    custom_role_repo = MagicMock()
    custom_role_repo.get = AsyncMock(return_value=role)
    custom_role_repo.soft_delete = AsyncMock()

    member_repo = MagicMock()
    member_repo.clear_custom_role_assignments = AsyncMock(return_value=2)

    service = RbacService(custom_role_repo=custom_role_repo, workspace_member_repo=member_repo)

    await service.delete_role(
        role_id=role_id,
        workspace_id=workspace_id,
        session=MagicMock(),
    )

    member_repo.clear_custom_role_assignments.assert_called_once()
    custom_role_repo.soft_delete.assert_called_once_with(role_id, workspace_id)
