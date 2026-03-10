"""Unit tests for RoleSkillRepository and RoleTemplateRepository.

Tests CRUD operations, workspace-scoped queries, and template access.
Uses SQLite in-memory database via db_session fixture.

Source: 011-role-based-skills, T007
"""

from __future__ import annotations

import uuid as _uuid_mod
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from pilot_space.infrastructure.database.models import (
    User,
    Workspace,
)
from pilot_space.infrastructure.database.models.user_role_skill import (
    RoleTemplate,
    UserRoleSkill,
)
from pilot_space.infrastructure.database.repositories.role_skill_repository import (
    RoleSkillRepository,
    RoleTemplateRepository,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Local SQLite schema (avoids PostgreSQL-specific syntax in shared conftest)
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    default_sdlc_role TEXT,
    bio TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    settings TEXT DEFAULT '{}',
    audit_retention_days INTEGER,
    rate_limit_standard_rpm INTEGER,
    rate_limit_ai_rpm INTEGER,
    storage_quota_mb INTEGER,
    storage_used_bytes INTEGER DEFAULT 0 NOT NULL,
    owner_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS workspace_members (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'MEMBER',
    weekly_available_hours INTEGER,
    custom_role_id TEXT,
    is_active BOOLEAN DEFAULT 1 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME,
    UNIQUE (user_id, workspace_id)
);

CREATE TABLE IF NOT EXISTS user_role_skills (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    role_type TEXT NOT NULL,
    role_name TEXT NOT NULL,
    skill_content TEXT NOT NULL,
    experience_description TEXT,
    is_primary BOOLEAN DEFAULT 0 NOT NULL,
    template_version INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME,
    UNIQUE (user_id, workspace_id, role_type)
);

CREATE TABLE IF NOT EXISTS role_templates (
    id TEXT PRIMARY KEY,
    role_type TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    default_skill_content TEXT NOT NULL DEFAULT '',
    icon TEXT NOT NULL DEFAULT 'code',
    sort_order INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);
"""


def _register_sqlite_fns(dbapi_conn: Any, connection_record: Any) -> None:
    dbapi_conn.create_function("gen_random_uuid", 0, lambda: str(_uuid_mod.uuid4()))


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    event.listen(engine.sync_engine, "connect", _register_sqlite_fns)
    async with engine.begin() as conn:
        for stmt in _SCHEMA_SQL.strip().split(";"):
            cleaned = stmt.strip()
            if cleaned:
                await conn.execute(text(cleaned))
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session, session.begin():
        yield session


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def workspace(db_session: AsyncSession) -> Workspace:
    """Create a workspace for tests."""
    ws = Workspace(
        id=uuid4(),
        name="Test Workspace",
        slug="test-role-ws",
        owner_id=uuid4(),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def other_workspace(db_session: AsyncSession) -> Workspace:
    """Create a second workspace for isolation tests."""
    ws = Workspace(
        id=uuid4(),
        name="Other Workspace",
        slug="other-role-ws",
        owner_id=uuid4(),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    """Create a user for tests."""
    u = User(
        id=uuid4(),
        email="roleuser@example.com",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create a second user for isolation tests."""
    u = User(
        id=uuid4(),
        email="otheruser@example.com",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def role_skill(
    db_session: AsyncSession,
    user: User,
    workspace: Workspace,
) -> UserRoleSkill:
    """Create a primary developer role skill."""
    skill = UserRoleSkill(
        id=uuid4(),
        user_id=user.id,
        workspace_id=workspace.id,
        role_type="developer",
        role_name="Senior Developer",
        skill_content="# Developer\n\nYou assist a developer.",
        experience_description="5 years Python, TypeScript",
        is_primary=True,
        template_version=1,
    )
    db_session.add(skill)
    await db_session.flush()
    return skill


@pytest.fixture
async def secondary_skill(
    db_session: AsyncSession,
    user: User,
    workspace: Workspace,
) -> UserRoleSkill:
    """Create a secondary architect role skill."""
    skill = UserRoleSkill(
        id=uuid4(),
        user_id=user.id,
        workspace_id=workspace.id,
        role_type="architect",
        role_name="Solution Architect",
        skill_content="# Architect\n\nYou assist an architect.",
        is_primary=False,
        template_version=1,
    )
    db_session.add(skill)
    await db_session.flush()
    return skill


@pytest.fixture
async def role_templates(db_session: AsyncSession) -> list[RoleTemplate]:
    """Seed role templates for tests."""
    templates = []
    template_data = [
        ("developer", "Developer", "Code quality", "Code", 1),
        ("tester", "Tester", "Test strategy", "TestTube", 2),
        ("architect", "Architect", "System design", "Layers", 3),
    ]
    for role_type, display_name, desc, icon, order in template_data:
        t = RoleTemplate(
            id=uuid4(),
            role_type=role_type,
            display_name=display_name,
            description=desc,
            default_skill_content=f"# {display_name}\n\nDefault content.",
            icon=icon,
            sort_order=order,
            version=1,
        )
        db_session.add(t)
        templates.append(t)
    await db_session.flush()
    return templates


# ============================================================================
# RoleSkillRepository Tests
# ============================================================================


class TestGetByUserWorkspace:
    """Tests for get_by_user_workspace()."""

    async def test_returns_skills_for_user_workspace(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        role_skill: UserRoleSkill,
        secondary_skill: UserRoleSkill,
    ) -> None:
        """Returns all skills for user in workspace."""
        repo = RoleSkillRepository(db_session)
        results = await repo.get_by_user_workspace(user.id, workspace.id)

        assert len(results) == 2

    async def test_primary_skill_first(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        role_skill: UserRoleSkill,
        secondary_skill: UserRoleSkill,
    ) -> None:
        """Primary skill appears before secondary skills."""
        repo = RoleSkillRepository(db_session)
        results = await repo.get_by_user_workspace(user.id, workspace.id)

        assert results[0].is_primary is True
        assert results[0].role_type == "developer"

    async def test_empty_for_different_workspace(
        self,
        db_session: AsyncSession,
        user: User,
        other_workspace: Workspace,
        role_skill: UserRoleSkill,
    ) -> None:
        """Returns empty for workspace where user has no skills."""
        repo = RoleSkillRepository(db_session)
        results = await repo.get_by_user_workspace(user.id, other_workspace.id)

        assert len(results) == 0

    async def test_empty_for_different_user(
        self,
        db_session: AsyncSession,
        other_user: User,
        workspace: Workspace,
        role_skill: UserRoleSkill,
    ) -> None:
        """Returns empty for user who has no skills in workspace."""
        repo = RoleSkillRepository(db_session)
        results = await repo.get_by_user_workspace(other_user.id, workspace.id)

        assert len(results) == 0

    async def test_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        role_skill: UserRoleSkill,
    ) -> None:
        """Soft-deleted skills are excluded."""
        role_skill.soft_delete()
        await db_session.flush()

        repo = RoleSkillRepository(db_session)
        results = await repo.get_by_user_workspace(user.id, workspace.id)

        assert len(results) == 0


class TestGetPrimaryByUserWorkspace:
    """Tests for get_primary_by_user_workspace()."""

    async def test_returns_primary_skill(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        role_skill: UserRoleSkill,
        secondary_skill: UserRoleSkill,
    ) -> None:
        """Returns only the primary skill."""
        repo = RoleSkillRepository(db_session)
        result = await repo.get_primary_by_user_workspace(user.id, workspace.id)

        assert result is not None
        assert result.is_primary is True
        assert result.role_type == "developer"

    async def test_returns_none_when_no_primary(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        secondary_skill: UserRoleSkill,
    ) -> None:
        """Returns None when no primary skill exists."""
        repo = RoleSkillRepository(db_session)
        result = await repo.get_primary_by_user_workspace(user.id, workspace.id)

        assert result is None


class TestCountByUserWorkspace:
    """Tests for count_by_user_workspace()."""

    async def test_returns_correct_count(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        role_skill: UserRoleSkill,
        secondary_skill: UserRoleSkill,
    ) -> None:
        """Returns accurate count of active skills."""
        repo = RoleSkillRepository(db_session)
        count = await repo.count_by_user_workspace(user.id, workspace.id)

        assert count == 2

    async def test_returns_zero_for_no_skills(
        self,
        db_session: AsyncSession,
        user: User,
        other_workspace: Workspace,
    ) -> None:
        """Returns 0 for workspace with no skills."""
        repo = RoleSkillRepository(db_session)
        count = await repo.count_by_user_workspace(user.id, other_workspace.id)

        assert count == 0

    async def test_excludes_soft_deleted_from_count(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        role_skill: UserRoleSkill,
        secondary_skill: UserRoleSkill,
    ) -> None:
        """Soft-deleted skills are not counted."""
        role_skill.soft_delete()
        await db_session.flush()

        repo = RoleSkillRepository(db_session)
        count = await repo.count_by_user_workspace(user.id, workspace.id)

        assert count == 1


class TestGetByUserWorkspaceRoleType:
    """Tests for get_by_user_workspace_role_type()."""

    async def test_returns_matching_skill(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        role_skill: UserRoleSkill,
    ) -> None:
        """Returns the skill matching user, workspace, and role type."""
        repo = RoleSkillRepository(db_session)
        result = await repo.get_by_user_workspace_role_type(user.id, workspace.id, "developer")

        assert result is not None
        assert result.role_type == "developer"
        assert result.role_name == "Senior Developer"

    async def test_returns_none_for_nonexistent_role_type(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        role_skill: UserRoleSkill,
    ) -> None:
        """Returns None when role type does not exist for user-workspace."""
        repo = RoleSkillRepository(db_session)
        result = await repo.get_by_user_workspace_role_type(user.id, workspace.id, "tester")

        assert result is None


class TestRoleSkillCRUD:
    """Tests for create, update, delete operations via BaseRepository."""

    async def test_create_role_skill(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
    ) -> None:
        """Create a new role skill and verify persistence."""
        repo = RoleSkillRepository(db_session)
        skill = UserRoleSkill(
            user_id=user.id,
            workspace_id=workspace.id,
            role_type="tester",
            role_name="QA Engineer",
            skill_content="# Tester\n\nTest content.",
            is_primary=False,
        )
        created = await repo.create(skill)

        assert created.id is not None
        assert created.role_type == "tester"
        assert created.role_name == "QA Engineer"

    async def test_update_skill_content(
        self,
        db_session: AsyncSession,
        role_skill: UserRoleSkill,
    ) -> None:
        """Update skill content and verify change."""
        repo = RoleSkillRepository(db_session)
        role_skill.skill_content = "# Developer\n\nUpdated content."
        updated = await repo.update(role_skill)

        assert "Updated content" in updated.skill_content

    async def test_soft_delete_skill(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        role_skill: UserRoleSkill,
    ) -> None:
        """Soft delete removes skill from active queries."""
        repo = RoleSkillRepository(db_session)
        await repo.delete(role_skill)

        results = await repo.get_by_user_workspace(user.id, workspace.id)
        assert len(results) == 0

    async def test_get_by_id_returns_skill(
        self,
        db_session: AsyncSession,
        role_skill: UserRoleSkill,
    ) -> None:
        """Get by ID returns the correct skill."""
        repo = RoleSkillRepository(db_session)
        result = await repo.get_by_id(role_skill.id)

        assert result is not None
        assert result.id == role_skill.id

    async def test_get_by_id_returns_none_for_nonexistent(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Get by ID returns None for non-existent ID."""
        repo = RoleSkillRepository(db_session)
        result = await repo.get_by_id(uuid4())

        assert result is None


# ============================================================================
# RoleTemplateRepository Tests
# ============================================================================


class TestGetAllOrdered:
    """Tests for get_all_ordered()."""

    async def test_returns_templates_in_sort_order(
        self,
        db_session: AsyncSession,
        role_templates: list[RoleTemplate],
    ) -> None:
        """Returns all templates sorted by sort_order."""
        repo = RoleTemplateRepository(db_session)
        results = await repo.get_all_ordered()

        assert len(results) == 3
        assert results[0].role_type == "developer"
        assert results[1].role_type == "tester"
        assert results[2].role_type == "architect"

    async def test_returns_empty_when_no_templates(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Returns empty list when no templates exist."""
        repo = RoleTemplateRepository(db_session)
        results = await repo.get_all_ordered()

        assert len(results) == 0

    async def test_excludes_soft_deleted_templates(
        self,
        db_session: AsyncSession,
        role_templates: list[RoleTemplate],
    ) -> None:
        """Soft-deleted templates are excluded."""
        role_templates[0].soft_delete()
        await db_session.flush()

        repo = RoleTemplateRepository(db_session)
        results = await repo.get_all_ordered()

        assert len(results) == 2


class TestGetByRoleType:
    """Tests for get_by_role_type()."""

    async def test_returns_matching_template(
        self,
        db_session: AsyncSession,
        role_templates: list[RoleTemplate],
    ) -> None:
        """Returns the template matching the role type."""
        repo = RoleTemplateRepository(db_session)
        result = await repo.get_by_role_type("developer")

        assert result is not None
        assert result.display_name == "Developer"
        assert result.icon == "Code"

    async def test_returns_none_for_nonexistent_type(
        self,
        db_session: AsyncSession,
        role_templates: list[RoleTemplate],
    ) -> None:
        """Returns None for non-existent role type."""
        repo = RoleTemplateRepository(db_session)
        result = await repo.get_by_role_type("nonexistent")

        assert result is None

    async def test_template_has_default_content(
        self,
        db_session: AsyncSession,
        role_templates: list[RoleTemplate],
    ) -> None:
        """Template includes default skill content."""
        repo = RoleTemplateRepository(db_session)
        result = await repo.get_by_role_type("developer")

        assert result is not None
        assert "Default content" in result.default_skill_content
