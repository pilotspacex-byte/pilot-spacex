"""Unit tests for SkillVersionRepository.

Tests create and read operations. No update tests -- versions are immutable.
Uses SQLite in-memory database via local fixtures.

Source: Phase 50, P50-03
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

from pilot_space.infrastructure.database.models import Workspace
from pilot_space.infrastructure.database.models.skill_marketplace_listing import (
    SkillMarketplaceListing,
)
from pilot_space.infrastructure.database.repositories.skill_marketplace_listing_repository import (
    SkillMarketplaceListingRepository,
)
from pilot_space.infrastructure.database.repositories.skill_version_repository import (
    SkillVersionRepository,
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

CREATE TABLE IF NOT EXISTS skill_marketplace_listings (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    long_description TEXT,
    author TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT 'Wand2',
    category TEXT NOT NULL,
    tags TEXT DEFAULT '[]',
    version TEXT NOT NULL,
    download_count INTEGER NOT NULL DEFAULT 0,
    avg_rating REAL,
    screenshots TEXT,
    graph_data TEXT,
    published_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS skill_versions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    listing_id TEXT NOT NULL REFERENCES skill_marketplace_listings(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    skill_content TEXT NOT NULL,
    graph_data TEXT,
    changelog TEXT,
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
        slug="test-version-ws",
        owner_id=uuid4(),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def listing(
    db_session: AsyncSession,
    workspace: Workspace,
) -> SkillMarketplaceListing:
    repo = SkillMarketplaceListingRepository(db_session)
    return await repo.create(
        workspace_id=workspace.id,
        name="Test Skill",
        description="A skill for testing",
        author="Author",
        category="testing",
        version="1.0.0",
    )


@pytest.fixture
async def repo(db_session: AsyncSession) -> SkillVersionRepository:
    return SkillVersionRepository(db_session)


# ============================================================================
# Tests
# ============================================================================


class TestCreateVersion:
    """Tests for create()."""

    async def test_create_version(
        self,
        repo: SkillVersionRepository,
        workspace: Workspace,
        listing: SkillMarketplaceListing,
    ) -> None:
        """Create a version and verify all fields."""
        version = await repo.create(
            workspace_id=workspace.id,
            listing_id=listing.id,
            version="1.0.0",
            skill_content="# Test Skill\n\nContent.",
            changelog="Initial release",
        )

        assert version.id is not None
        assert version.listing_id == listing.id
        assert version.version == "1.0.0"
        assert version.skill_content == "# Test Skill\n\nContent."
        assert version.changelog == "Initial release"
        assert version.graph_data is None
        assert version.is_deleted is False


class TestGetByListing:
    """Tests for get_by_listing()."""

    async def test_get_versions_by_listing(
        self,
        db_session: AsyncSession,
        repo: SkillVersionRepository,
        workspace: Workspace,
        listing: SkillMarketplaceListing,
    ) -> None:
        """Creates 2 versions, verifies listing filter and count."""
        from datetime import UTC, datetime, timedelta

        v1 = await repo.create(
            workspace_id=workspace.id,
            listing_id=listing.id,
            version="1.0.0",
            skill_content="# V1",
        )
        # Manually set created_at to ensure deterministic ordering
        # (SQLite CURRENT_TIMESTAMP has second-level precision)
        v1.created_at = datetime(2025, 1, 1, tzinfo=UTC)
        await db_session.flush()

        v2 = await repo.create(
            workspace_id=workspace.id,
            listing_id=listing.id,
            version="2.0.0",
            skill_content="# V2",
        )
        v2.created_at = datetime(2025, 1, 2, tzinfo=UTC)
        await db_session.flush()

        versions = await repo.get_by_listing(listing.id)
        assert len(versions) == 2
        # Newest first (v2 has later created_at)
        assert versions[0].version == "2.0.0"
        assert versions[1].version == "1.0.0"

    async def test_empty_listing(
        self,
        repo: SkillVersionRepository,
        listing: SkillMarketplaceListing,
    ) -> None:
        """Returns empty list for listing with no versions."""
        versions = await repo.get_by_listing(listing.id)
        assert len(versions) == 0


class TestGetLatestByListing:
    """Tests for get_latest_by_listing()."""

    async def test_returns_latest(
        self,
        db_session: AsyncSession,
        repo: SkillVersionRepository,
        workspace: Workspace,
        listing: SkillMarketplaceListing,
    ) -> None:
        """Returns the most recently created version."""
        from datetime import UTC, datetime

        v1 = await repo.create(
            workspace_id=workspace.id,
            listing_id=listing.id,
            version="1.0.0",
            skill_content="# V1",
        )
        v1.created_at = datetime(2025, 1, 1, tzinfo=UTC)
        await db_session.flush()

        v2 = await repo.create(
            workspace_id=workspace.id,
            listing_id=listing.id,
            version="2.0.0",
            skill_content="# V2",
        )
        v2.created_at = datetime(2025, 1, 2, tzinfo=UTC)
        await db_session.flush()

        latest = await repo.get_latest_by_listing(listing.id)
        assert latest is not None
        assert latest.version == "2.0.0"

    async def test_returns_none_for_empty(
        self,
        repo: SkillVersionRepository,
        listing: SkillMarketplaceListing,
    ) -> None:
        """Returns None when no versions exist."""
        latest = await repo.get_latest_by_listing(listing.id)
        assert latest is None


class TestImmutability:
    """Verify SkillVersionRepository enforces immutability."""

    async def test_version_has_no_update_method(
        self,
        repo: SkillVersionRepository,
    ) -> None:
        """SkillVersionRepository does not define its own update method.

        Note: BaseRepository.update() exists but the repository class
        intentionally does not override or expose a typed update signature,
        signaling that versions should not be modified.
        """
        # The class itself should NOT define an 'update' method
        assert "update" not in SkillVersionRepository.__dict__
