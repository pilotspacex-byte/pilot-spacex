"""Unit tests for SkillTemplateRepository.

Tests CRUD operations and workspace-scoped queries.
Uses SQLite in-memory database via local fixtures.

Source: Phase 20, P20-01
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
from pilot_space.infrastructure.database.repositories.skill_template_repository import (
    SkillTemplateRepository,
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
        slug="test-skill-ws",
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
        slug="other-skill-ws",
        owner_id=uuid4(),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    u = User(id=uuid4(), email="admin@example.com")
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def built_in_template(
    db_session: AsyncSession,
    workspace: Workspace,
) -> SkillTemplate:
    """Create a built-in skill template."""
    t = SkillTemplate(
        id=uuid4(),
        workspace_id=workspace.id,
        name="Developer",
        description="Code quality and best practices",
        skill_content="# Developer\n\nDefault developer content.",
        icon="Code",
        sort_order=1,
        source="built_in",
        role_type="developer",
        is_active=True,
    )
    db_session.add(t)
    await db_session.flush()
    return t


@pytest.fixture
async def workspace_template(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
) -> SkillTemplate:
    """Create a workspace skill template."""
    t = SkillTemplate(
        id=uuid4(),
        workspace_id=workspace.id,
        name="Security Expert",
        description="Security-focused skill",
        skill_content="# Security Expert\n\nSecurity content.",
        icon="Shield",
        sort_order=10,
        source="workspace",
        role_type=None,
        is_active=True,
        created_by=user.id,
    )
    db_session.add(t)
    await db_session.flush()
    return t


@pytest.fixture
async def inactive_template(
    db_session: AsyncSession,
    workspace: Workspace,
) -> SkillTemplate:
    """Create an inactive skill template."""
    t = SkillTemplate(
        id=uuid4(),
        workspace_id=workspace.id,
        name="Inactive Skill",
        description="Deactivated template",
        skill_content="# Inactive\n\nContent.",
        sort_order=99,
        source="workspace",
        is_active=False,
    )
    db_session.add(t)
    await db_session.flush()
    return t


# ============================================================================
# SkillTemplateRepository Tests
# ============================================================================


class TestCreateSkillTemplate:
    """Tests for create()."""

    async def test_create_built_in_template(
        self,
        db_session: AsyncSession,
        workspace: Workspace,
    ) -> None:
        """Create a built-in template and verify fields."""
        repo = SkillTemplateRepository(db_session)
        template = await repo.create(
            workspace_id=workspace.id,
            name="Tester",
            description="Testing skills",
            skill_content="# Tester\n\nContent.",
            source="built_in",
            role_type="tester",
            icon="TestTube",
            sort_order=2,
        )

        assert template.id is not None
        assert template.name == "Tester"
        assert template.source == "built_in"
        assert template.role_type == "tester"
        assert template.is_active is True
        assert template.is_deleted is False

    async def test_create_workspace_template_with_creator(
        self,
        db_session: AsyncSession,
        workspace: Workspace,
        user: User,
    ) -> None:
        """Create a workspace template with created_by."""
        repo = SkillTemplateRepository(db_session)
        template = await repo.create(
            workspace_id=workspace.id,
            name="Custom Skill",
            description="Custom",
            skill_content="# Custom\n\nContent.",
            source="workspace",
            created_by=user.id,
        )

        assert template.source == "workspace"
        assert template.created_by == user.id
        assert template.role_type is None

    async def test_defaults_icon_and_sort_order(
        self,
        db_session: AsyncSession,
        workspace: Workspace,
    ) -> None:
        """Verify default values for icon and sort_order."""
        repo = SkillTemplateRepository(db_session)
        template = await repo.create(
            workspace_id=workspace.id,
            name="Minimal",
            description="Minimal template",
            skill_content="# Minimal\n\nContent.",
            source="workspace",
        )

        assert template.icon == "Wand2"
        assert template.sort_order == 0


class TestGetActiveByWorkspace:
    """Tests for get_active_by_workspace()."""

    async def test_returns_active_templates_only(
        self,
        db_session: AsyncSession,
        workspace: Workspace,
        built_in_template: SkillTemplate,
        workspace_template: SkillTemplate,
        inactive_template: SkillTemplate,
    ) -> None:
        """Returns only active, non-deleted templates."""
        repo = SkillTemplateRepository(db_session)
        results = await repo.get_active_by_workspace(workspace.id)

        assert len(results) == 2
        names = {t.name for t in results}
        assert "Developer" in names
        assert "Security Expert" in names
        assert "Inactive Skill" not in names

    async def test_ordered_by_sort_order(
        self,
        db_session: AsyncSession,
        workspace: Workspace,
        built_in_template: SkillTemplate,
        workspace_template: SkillTemplate,
    ) -> None:
        """Results ordered by sort_order ascending."""
        repo = SkillTemplateRepository(db_session)
        results = await repo.get_active_by_workspace(workspace.id)

        assert results[0].sort_order <= results[1].sort_order

    async def test_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        workspace: Workspace,
        built_in_template: SkillTemplate,
    ) -> None:
        """Soft-deleted templates excluded from active list."""
        built_in_template.soft_delete()
        await db_session.flush()

        repo = SkillTemplateRepository(db_session)
        results = await repo.get_active_by_workspace(workspace.id)

        assert len(results) == 0

    async def test_workspace_isolation(
        self,
        db_session: AsyncSession,
        other_workspace: Workspace,
        built_in_template: SkillTemplate,
    ) -> None:
        """Templates from other workspaces not returned."""
        repo = SkillTemplateRepository(db_session)
        results = await repo.get_active_by_workspace(other_workspace.id)

        assert len(results) == 0

    async def test_empty_workspace(
        self,
        db_session: AsyncSession,
        workspace: Workspace,
    ) -> None:
        """Returns empty list for workspace with no templates."""
        repo = SkillTemplateRepository(db_session)
        results = await repo.get_active_by_workspace(workspace.id)

        assert len(results) == 0


class TestGetByWorkspace:
    """Tests for get_by_workspace()."""

    async def test_returns_all_non_deleted_templates(
        self,
        db_session: AsyncSession,
        workspace: Workspace,
        built_in_template: SkillTemplate,
        workspace_template: SkillTemplate,
        inactive_template: SkillTemplate,
    ) -> None:
        """Returns all templates including inactive ones."""
        repo = SkillTemplateRepository(db_session)
        results = await repo.get_by_workspace(workspace.id)

        assert len(results) == 3

    async def test_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        workspace: Workspace,
        built_in_template: SkillTemplate,
        workspace_template: SkillTemplate,
    ) -> None:
        """Soft-deleted templates excluded."""
        built_in_template.soft_delete()
        await db_session.flush()

        repo = SkillTemplateRepository(db_session)
        results = await repo.get_by_workspace(workspace.id)

        assert len(results) == 1
        assert results[0].name == "Security Expert"


class TestUpdateSkillTemplate:
    """Tests for update()."""

    async def test_update_template_content(
        self,
        db_session: AsyncSession,
        workspace_template: SkillTemplate,
    ) -> None:
        """Update skill content and verify change."""
        repo = SkillTemplateRepository(db_session)
        workspace_template.skill_content = "# Security Expert\n\nUpdated content."
        updated = await repo.update(workspace_template)

        assert "Updated content" in updated.skill_content

    async def test_update_template_name(
        self,
        db_session: AsyncSession,
        workspace_template: SkillTemplate,
    ) -> None:
        """Update template name."""
        repo = SkillTemplateRepository(db_session)
        workspace_template.name = "Security Specialist"
        updated = await repo.update(workspace_template)

        assert updated.name == "Security Specialist"


class TestSoftDeleteSkillTemplate:
    """Tests for soft_delete()."""

    async def test_soft_delete_sets_flags(
        self,
        db_session: AsyncSession,
        workspace: Workspace,
        built_in_template: SkillTemplate,
    ) -> None:
        """Soft delete sets is_deleted, deleted_at, and is_active=False."""
        repo = SkillTemplateRepository(db_session)
        result = await repo.soft_delete(built_in_template.id)

        assert result is not None
        assert result.is_deleted is True
        assert result.deleted_at is not None
        assert result.is_active is False

    async def test_soft_delete_removes_from_active(
        self,
        db_session: AsyncSession,
        workspace: Workspace,
        built_in_template: SkillTemplate,
    ) -> None:
        """After soft delete, template excluded from active list."""
        repo = SkillTemplateRepository(db_session)
        await repo.soft_delete(built_in_template.id)

        results = await repo.get_active_by_workspace(workspace.id)
        assert len(results) == 0

    async def test_soft_delete_nonexistent_returns_none(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Soft-deleting non-existent ID returns None."""
        repo = SkillTemplateRepository(db_session)
        result = await repo.soft_delete(uuid4())

        assert result is None


class TestGetById:
    """Tests for get_by_id() inherited from BaseRepository."""

    async def test_returns_template_by_id(
        self,
        db_session: AsyncSession,
        built_in_template: SkillTemplate,
    ) -> None:
        """Get by ID returns the correct template."""
        repo = SkillTemplateRepository(db_session)
        result = await repo.get_by_id(built_in_template.id)

        assert result is not None
        assert result.id == built_in_template.id
        assert result.name == "Developer"

    async def test_returns_none_for_nonexistent(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Get by ID returns None for non-existent ID."""
        repo = SkillTemplateRepository(db_session)
        result = await repo.get_by_id(uuid4())

        assert result is None
