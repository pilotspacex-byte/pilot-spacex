"""Unit tests for UserSkillRepository.

Tests CRUD operations and user-workspace-scoped queries.
Uses SQLite in-memory database via local fixtures.

Source: Phase 20, P20-02
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

from pilot_space.infrastructure.database.models import User, Workspace
from pilot_space.infrastructure.database.models.skill_template import SkillTemplate
from pilot_space.infrastructure.database.models.user_skill import UserSkill
from pilot_space.infrastructure.database.repositories.user_skill_repository import (
    UserSkillRepository,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Local SQLite schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    default_sdlc_role TEXT,
    bio TEXT,
    ai_settings TEXT,
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

CREATE TABLE IF NOT EXISTS skill_templates (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    skill_content TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT 'Wand2',
    sort_order INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL,
    role_type TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
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

CREATE TABLE IF NOT EXISTS user_skills (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    template_id TEXT REFERENCES skill_templates(id) ON DELETE SET NULL,
    skill_content TEXT NOT NULL,
    experience_description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
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
    ws = Workspace(
        id=uuid4(),
        name="Test Workspace",
        slug="test-uskill-ws",
        owner_id=uuid4(),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def other_workspace(db_session: AsyncSession) -> Workspace:
    ws = Workspace(
        id=uuid4(),
        name="Other Workspace",
        slug="other-uskill-ws",
        owner_id=uuid4(),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    u = User(id=uuid4(), email="skilluser@example.com")
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    u = User(id=uuid4(), email="otherskilluser@example.com")
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def template(
    db_session: AsyncSession,
    workspace: Workspace,
) -> SkillTemplate:
    """Create a skill template for linking."""
    t = SkillTemplate(
        id=uuid4(),
        workspace_id=workspace.id,
        name="Developer",
        description="Developer template",
        skill_content="# Developer\n\nDefault content.",
        source="built_in",
        role_type="developer",
        is_active=True,
    )
    db_session.add(t)
    await db_session.flush()
    return t


@pytest.fixture
async def second_template(
    db_session: AsyncSession,
    workspace: Workspace,
) -> SkillTemplate:
    """Create a second template for testing multiple skills."""
    t = SkillTemplate(
        id=uuid4(),
        workspace_id=workspace.id,
        name="Tester",
        description="Tester template",
        skill_content="# Tester\n\nDefault content.",
        source="built_in",
        role_type="tester",
        is_active=True,
    )
    db_session.add(t)
    await db_session.flush()
    return t


@pytest.fixture
async def user_skill(
    db_session: AsyncSession,
    user: User,
    workspace: Workspace,
    template: SkillTemplate,
) -> UserSkill:
    """Create a user skill linked to template."""
    s = UserSkill(
        id=uuid4(),
        user_id=user.id,
        workspace_id=workspace.id,
        template_id=template.id,
        skill_content="# Developer\n\nPersonalized developer content.",
        experience_description="5 years Python",
        is_active=True,
    )
    db_session.add(s)
    await db_session.flush()
    return s


@pytest.fixture
async def second_user_skill(
    db_session: AsyncSession,
    user: User,
    workspace: Workspace,
    second_template: SkillTemplate,
) -> UserSkill:
    """Create a second user skill linked to another template."""
    s = UserSkill(
        id=uuid4(),
        user_id=user.id,
        workspace_id=workspace.id,
        template_id=second_template.id,
        skill_content="# Tester\n\nPersonalized tester content.",
        is_active=True,
    )
    db_session.add(s)
    await db_session.flush()
    return s


# ============================================================================
# UserSkillRepository Tests
# ============================================================================


class TestCreateUserSkill:
    """Tests for create()."""

    async def test_create_skill_with_template(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        template: SkillTemplate,
    ) -> None:
        """Create a user skill linked to a template."""
        repo = UserSkillRepository(db_session)
        skill = await repo.create(
            user_id=user.id,
            workspace_id=workspace.id,
            template_id=template.id,
            skill_content="# Developer\n\nCustom content.",
            experience_description="10 years Java",
        )

        assert skill.id is not None
        assert skill.user_id == user.id
        assert skill.template_id == template.id
        assert skill.is_active is True
        assert skill.is_deleted is False

    async def test_create_skill_without_template(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
    ) -> None:
        """Create a user skill without a template (custom skill)."""
        repo = UserSkillRepository(db_session)
        skill = await repo.create(
            user_id=user.id,
            workspace_id=workspace.id,
            skill_content="# Custom\n\nFreeform content.",
        )

        assert skill.id is not None
        assert skill.template_id is None
        assert skill.experience_description is None


class TestGetByUserWorkspace:
    """Tests for get_by_user_workspace()."""

    async def test_returns_active_skills(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        user_skill: UserSkill,
        second_user_skill: UserSkill,
    ) -> None:
        """Returns all active, non-deleted skills for user in workspace."""
        repo = UserSkillRepository(db_session)
        results = await repo.get_by_user_workspace(user.id, workspace.id)

        assert len(results) == 2

    async def test_excludes_inactive_skills(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        user_skill: UserSkill,
    ) -> None:
        """Inactive skills excluded from results."""
        user_skill.is_active = False
        await db_session.flush()

        repo = UserSkillRepository(db_session)
        results = await repo.get_by_user_workspace(user.id, workspace.id)

        assert len(results) == 0

    async def test_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        user_skill: UserSkill,
    ) -> None:
        """Soft-deleted skills excluded."""
        user_skill.soft_delete()
        await db_session.flush()

        repo = UserSkillRepository(db_session)
        results = await repo.get_by_user_workspace(user.id, workspace.id)

        assert len(results) == 0

    async def test_workspace_isolation(
        self,
        db_session: AsyncSession,
        user: User,
        other_workspace: Workspace,
        user_skill: UserSkill,
    ) -> None:
        """Skills from other workspaces not returned."""
        repo = UserSkillRepository(db_session)
        results = await repo.get_by_user_workspace(user.id, other_workspace.id)

        assert len(results) == 0

    async def test_user_isolation(
        self,
        db_session: AsyncSession,
        other_user: User,
        workspace: Workspace,
        user_skill: UserSkill,
    ) -> None:
        """Skills from other users not returned."""
        repo = UserSkillRepository(db_session)
        results = await repo.get_by_user_workspace(other_user.id, workspace.id)

        assert len(results) == 0

    async def test_empty_when_no_skills(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
    ) -> None:
        """Returns empty list when user has no skills."""
        repo = UserSkillRepository(db_session)
        results = await repo.get_by_user_workspace(user.id, workspace.id)

        assert len(results) == 0


class TestGetByUserWorkspaceTemplate:
    """Tests for get_by_user_workspace_template()."""

    async def test_returns_matching_skill(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        template: SkillTemplate,
        user_skill: UserSkill,
    ) -> None:
        """Returns the skill matching user, workspace, and template."""
        repo = UserSkillRepository(db_session)
        result = await repo.get_by_user_workspace_template(user.id, workspace.id, template.id)

        assert result is not None
        assert result.template_id == template.id

    async def test_returns_none_for_unlinked_template(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        second_template: SkillTemplate,
        user_skill: UserSkill,
    ) -> None:
        """Returns None when user has no skill from the given template."""
        repo = UserSkillRepository(db_session)
        result = await repo.get_by_user_workspace_template(
            user.id, workspace.id, second_template.id
        )

        assert result is None

    async def test_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        template: SkillTemplate,
        user_skill: UserSkill,
    ) -> None:
        """Soft-deleted skills not returned."""
        user_skill.soft_delete()
        await db_session.flush()

        repo = UserSkillRepository(db_session)
        result = await repo.get_by_user_workspace_template(user.id, workspace.id, template.id)

        assert result is None


class TestUpdateUserSkill:
    """Tests for update()."""

    async def test_update_skill_content(
        self,
        db_session: AsyncSession,
        user_skill: UserSkill,
    ) -> None:
        """Update skill content and verify change."""
        repo = UserSkillRepository(db_session)
        user_skill.skill_content = "# Developer\n\nUpdated content."
        updated = await repo.update(user_skill)

        assert "Updated content" in updated.skill_content

    async def test_update_experience_description(
        self,
        db_session: AsyncSession,
        user_skill: UserSkill,
    ) -> None:
        """Update experience description."""
        repo = UserSkillRepository(db_session)
        user_skill.experience_description = "10 years Python + TypeScript"
        updated = await repo.update(user_skill)

        assert updated.experience_description == "10 years Python + TypeScript"


class TestSoftDeleteUserSkill:
    """Tests for soft_delete()."""

    async def test_soft_delete_sets_flags(
        self,
        db_session: AsyncSession,
        user_skill: UserSkill,
    ) -> None:
        """Soft delete sets is_deleted, deleted_at, and is_active=False."""
        repo = UserSkillRepository(db_session)
        result = await repo.soft_delete(user_skill.id)

        assert result is not None
        assert result.is_deleted is True
        assert result.deleted_at is not None
        assert result.is_active is False

    async def test_soft_delete_removes_from_active(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        user_skill: UserSkill,
    ) -> None:
        """After soft delete, skill excluded from active list."""
        repo = UserSkillRepository(db_session)
        await repo.soft_delete(user_skill.id)

        results = await repo.get_by_user_workspace(user.id, workspace.id)
        assert len(results) == 0

    async def test_soft_delete_nonexistent_returns_none(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Soft-deleting non-existent ID returns None."""
        repo = UserSkillRepository(db_session)
        result = await repo.soft_delete(uuid4())

        assert result is None


class TestGetById:
    """Tests for get_by_id() inherited from BaseRepository."""

    async def test_returns_skill_by_id(
        self,
        db_session: AsyncSession,
        user_skill: UserSkill,
    ) -> None:
        """Get by ID returns the correct skill."""
        repo = UserSkillRepository(db_session)
        result = await repo.get_by_id(user_skill.id)

        assert result is not None
        assert result.id == user_skill.id

    async def test_returns_none_for_nonexistent(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Get by ID returns None for non-existent ID."""
        repo = UserSkillRepository(db_session)
        result = await repo.get_by_id(uuid4())

        assert result is None
