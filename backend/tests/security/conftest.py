"""Security test fixtures.

Provides fixtures for RLS and rate limiting tests including:
- Test users with different roles (owner, admin, member, guest, outsider)
- Test workspaces with isolation
- Database session management with RLS context
- Redis client mocking for rate limiting
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from pilot_space.infrastructure.database.base import Base
from pilot_space.infrastructure.database.models.user import User
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


# =============================================================================
# Test Data Classes
# =============================================================================


@dataclass
class TestUser:
    """Test user data container."""

    id: uuid.UUID
    email: str
    full_name: str
    model: User | None = None


@dataclass
class TestWorkspace:
    """Test workspace data container."""

    id: uuid.UUID
    name: str
    slug: str
    model: Workspace | None = None


@dataclass
class TestWorkspaceMember:
    """Test workspace member data container."""

    user: TestUser
    workspace: TestWorkspace
    role: WorkspaceRole


@dataclass
class SecurityTestContext:
    """Container for all security test fixtures."""

    owner: TestUser
    admin: TestUser
    member: TestUser
    guest: TestUser
    outsider: TestUser
    workspace_a: TestWorkspace
    workspace_b: TestWorkspace


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine.

    Uses SQLite for fast testing without PostgreSQL dependency.
    Note: RLS policies are PostgreSQL-specific, so some tests
    will be marked as integration tests requiring real PostgreSQL.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for testing.

    Yields:
        AsyncSession with transaction that rolls back after test.
    """
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


# =============================================================================
# User Fixtures
# =============================================================================


@pytest.fixture
def user_owner() -> TestUser:
    """Create test owner user."""
    return TestUser(
        id=uuid.uuid4(),
        email="owner@example.com",
        full_name="Test Owner",
    )


@pytest.fixture
def user_admin() -> TestUser:
    """Create test admin user."""
    return TestUser(
        id=uuid.uuid4(),
        email="admin@example.com",
        full_name="Test Admin",
    )


@pytest.fixture
def user_member() -> TestUser:
    """Create test member user."""
    return TestUser(
        id=uuid.uuid4(),
        email="member@example.com",
        full_name="Test Member",
    )


@pytest.fixture
def user_guest() -> TestUser:
    """Create test guest user."""
    return TestUser(
        id=uuid.uuid4(),
        email="guest@example.com",
        full_name="Test Guest",
    )


@pytest.fixture
def user_outsider() -> TestUser:
    """Create test outsider user (not in any workspace)."""
    return TestUser(
        id=uuid.uuid4(),
        email="outsider@example.com",
        full_name="Test Outsider",
    )


# =============================================================================
# Workspace Fixtures
# =============================================================================


@pytest.fixture
def workspace_a(user_owner: TestUser) -> TestWorkspace:
    """Create test workspace A."""
    return TestWorkspace(
        id=uuid.uuid4(),
        name="Workspace A",
        slug="workspace-a",
    )


@pytest.fixture
def workspace_b() -> TestWorkspace:
    """Create test workspace B (isolated from workspace A)."""
    return TestWorkspace(
        id=uuid.uuid4(),
        name="Workspace B",
        slug="workspace-b",
    )


# =============================================================================
# Populated Database Fixtures
# =============================================================================


@pytest.fixture
async def populated_db(
    db_session: AsyncSession,
    user_owner: TestUser,
    user_admin: TestUser,
    user_member: TestUser,
    user_guest: TestUser,
    user_outsider: TestUser,
    workspace_a: TestWorkspace,
    workspace_b: TestWorkspace,
) -> SecurityTestContext:
    """Create populated database with users and workspaces.

    Sets up:
    - Workspace A with owner, admin, member, guest
    - Workspace B with separate owner (outsider to workspace A)
    - User "outsider" is not a member of any workspace

    Returns:
        SecurityTestContext with all test entities.
    """
    # Create users
    users_to_create = [user_owner, user_admin, user_member, user_guest, user_outsider]
    for test_user in users_to_create:
        user_model = User(
            id=test_user.id,
            email=test_user.email,
            full_name=test_user.full_name,
        )
        db_session.add(user_model)
        test_user.model = user_model

    # Create workspaces
    ws_a_model = Workspace(
        id=workspace_a.id,
        name=workspace_a.name,
        slug=workspace_a.slug,
        owner_id=user_owner.id,
    )
    db_session.add(ws_a_model)
    workspace_a.model = ws_a_model

    # Workspace B owned by outsider
    ws_b_model = Workspace(
        id=workspace_b.id,
        name=workspace_b.name,
        slug=workspace_b.slug,
        owner_id=user_outsider.id,
    )
    db_session.add(ws_b_model)
    workspace_b.model = ws_b_model

    # Create workspace memberships for Workspace A
    memberships = [
        WorkspaceMember(
            id=uuid.uuid4(),
            user_id=user_owner.id,
            workspace_id=workspace_a.id,
            role=WorkspaceRole.OWNER,
        ),
        WorkspaceMember(
            id=uuid.uuid4(),
            user_id=user_admin.id,
            workspace_id=workspace_a.id,
            role=WorkspaceRole.ADMIN,
        ),
        WorkspaceMember(
            id=uuid.uuid4(),
            user_id=user_member.id,
            workspace_id=workspace_a.id,
            role=WorkspaceRole.MEMBER,
        ),
        WorkspaceMember(
            id=uuid.uuid4(),
            user_id=user_guest.id,
            workspace_id=workspace_a.id,
            role=WorkspaceRole.GUEST,
        ),
    ]
    for membership in memberships:
        db_session.add(membership)

    # Outsider is owner of Workspace B (to test cross-workspace isolation)
    ws_b_membership = WorkspaceMember(
        id=uuid.uuid4(),
        user_id=user_outsider.id,
        workspace_id=workspace_b.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(ws_b_membership)

    await db_session.commit()

    return SecurityTestContext(
        owner=user_owner,
        admin=user_admin,
        member=user_member,
        guest=user_guest,
        outsider=user_outsider,
        workspace_a=workspace_a,
        workspace_b=workspace_b,
    )


# =============================================================================
# RLS Context Helpers
# =============================================================================


async def set_test_rls_context(
    session: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID | None = None,
) -> None:
    """Set RLS context for testing.

    Simulates Supabase auth context by setting PostgreSQL session variables.

    Args:
        session: Database session.
        user_id: Current user ID.
        workspace_id: Optional workspace context.
    """
    await session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
    if workspace_id:
        await session.execute(text(f"SET LOCAL app.current_workspace_id = '{workspace_id}'"))


async def clear_test_rls_context(session: AsyncSession) -> None:
    """Clear RLS context after test.

    Args:
        session: Database session.
    """
    await session.execute(text("RESET app.current_user_id"))
    await session.execute(text("RESET app.current_workspace_id"))


# =============================================================================
# Redis Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create mock Redis client for rate limiting tests."""
    redis = AsyncMock()

    # Track call counts per key for rate limit simulation
    call_counts: dict[str, int] = {}

    async def mock_incr(key: str) -> int:
        """Simulate Redis INCR."""
        call_counts[key] = call_counts.get(key, 0) + 1
        return call_counts[key]

    async def mock_expire(key: str, seconds: int) -> bool:
        """Simulate Redis EXPIRE."""
        return True

    async def mock_get(key: str) -> int | None:
        """Simulate Redis GET."""
        return call_counts.get(key)

    async def mock_set(key: str, value: int, ex: int | None = None) -> bool:
        """Simulate Redis SET."""
        call_counts[key] = value
        return True

    async def mock_delete(*keys: str) -> int:
        """Simulate Redis DELETE."""
        deleted = 0
        for key in keys:
            if key in call_counts:
                del call_counts[key]
                deleted += 1
        return deleted

    redis.incr = mock_incr
    redis.expire = mock_expire
    redis.get = mock_get
    redis.set = mock_set
    redis.delete = mock_delete
    redis._call_counts = call_counts  # Expose for test assertions

    return redis


@pytest.fixture
def reset_redis_counts(mock_redis: AsyncMock) -> None:
    """Reset Redis call counts between tests."""
    mock_redis._call_counts.clear()


# =============================================================================
# HTTP Client Fixtures
# =============================================================================


@pytest.fixture
def auth_headers(user_owner: TestUser) -> dict[str, str]:
    """Create auth headers for owner user."""
    # In real tests, this would be a valid JWT
    return {
        "Authorization": f"Bearer test-token-{user_owner.id}",
        "X-Workspace-ID": str(uuid.uuid4()),
    }


@pytest.fixture
def auth_headers_admin(user_admin: TestUser, workspace_a: TestWorkspace) -> dict[str, str]:
    """Create auth headers for admin user."""
    return {
        "Authorization": f"Bearer test-token-{user_admin.id}",
        "X-Workspace-ID": str(workspace_a.id),
    }


@pytest.fixture
def auth_headers_member(user_member: TestUser, workspace_a: TestWorkspace) -> dict[str, str]:
    """Create auth headers for member user."""
    return {
        "Authorization": f"Bearer test-token-{user_member.id}",
        "X-Workspace-ID": str(workspace_a.id),
    }


@pytest.fixture
def auth_headers_guest(user_guest: TestUser, workspace_a: TestWorkspace) -> dict[str, str]:
    """Create auth headers for guest user."""
    return {
        "Authorization": f"Bearer test-token-{user_guest.id}",
        "X-Workspace-ID": str(workspace_a.id),
    }


@pytest.fixture
def auth_headers_outsider(
    user_outsider: TestUser,
    workspace_b: TestWorkspace,
) -> dict[str, str]:
    """Create auth headers for outsider user."""
    return {
        "Authorization": f"Bearer test-token-{user_outsider.id}",
        "X-Workspace-ID": str(workspace_b.id),
    }
