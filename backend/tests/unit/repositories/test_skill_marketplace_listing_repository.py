"""Unit tests for SkillMarketplaceListingRepository.

Tests CRUD operations and marketplace query patterns.
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
        slug="test-marketplace-ws",
        owner_id=uuid4(),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def repo(db_session: AsyncSession) -> SkillMarketplaceListingRepository:
    return SkillMarketplaceListingRepository(db_session)


# ============================================================================
# Tests
# ============================================================================


class TestCreateListing:
    """Tests for create()."""

    async def test_create_listing(
        self,
        repo: SkillMarketplaceListingRepository,
        workspace: Workspace,
    ) -> None:
        """Create a listing and verify all fields."""
        listing = await repo.create(
            workspace_id=workspace.id,
            name="Code Reviewer",
            description="AI-powered code review",
            author="Pilot Space",
            category="development",
            version="1.0.0",
            long_description="Extended description here.",
            tags=["code", "review"],
        )

        assert listing.id is not None
        assert listing.name == "Code Reviewer"
        assert listing.description == "AI-powered code review"
        assert listing.author == "Pilot Space"
        assert listing.category == "development"
        assert listing.version == "1.0.0"
        assert listing.long_description == "Extended description here."
        assert listing.download_count == 0
        assert listing.avg_rating is None
        assert listing.icon == "Wand2"
        assert listing.is_deleted is False

    async def test_create_with_defaults(
        self,
        repo: SkillMarketplaceListingRepository,
        workspace: Workspace,
    ) -> None:
        """Create with minimal fields uses correct defaults."""
        listing = await repo.create(
            workspace_id=workspace.id,
            name="Minimal Skill",
            description="Minimal",
            author="Author",
            category="general",
            version="0.1.0",
        )

        assert listing.icon == "Wand2"
        assert listing.download_count == 0
        assert listing.tags == []
        assert listing.screenshots is None


class TestGetByCategory:
    """Tests for get_by_category()."""

    async def test_get_by_category(
        self,
        repo: SkillMarketplaceListingRepository,
        workspace: Workspace,
    ) -> None:
        """Creates 2 listings in same category, verifies filtered result."""
        await repo.create(
            workspace_id=workspace.id,
            name="Skill A",
            description="Desc A",
            author="Author",
            category="development",
            version="1.0.0",
        )
        await repo.create(
            workspace_id=workspace.id,
            name="Skill B",
            description="Desc B",
            author="Author",
            category="development",
            version="1.0.0",
        )
        await repo.create(
            workspace_id=workspace.id,
            name="Skill C",
            description="Desc C",
            author="Author",
            category="design",
            version="1.0.0",
        )

        results = await repo.get_by_category("development")
        assert len(results) == 2
        names = {r.name for r in results}
        assert names == {"Skill A", "Skill B"}

    async def test_excludes_deleted(
        self,
        db_session: AsyncSession,
        repo: SkillMarketplaceListingRepository,
        workspace: Workspace,
    ) -> None:
        """Soft-deleted listings excluded from category results."""
        listing = await repo.create(
            workspace_id=workspace.id,
            name="Deleted Skill",
            description="To be deleted",
            author="Author",
            category="development",
            version="1.0.0",
        )
        listing.is_deleted = True
        await db_session.flush()

        results = await repo.get_by_category("development")
        assert len(results) == 0


class TestSearch:
    """Tests for search()."""

    async def test_search_by_name(
        self,
        repo: SkillMarketplaceListingRepository,
        workspace: Workspace,
    ) -> None:
        """Search by partial name match."""
        await repo.create(
            workspace_id=workspace.id,
            name="Code Reviewer Pro",
            description="Reviews code",
            author="Author",
            category="development",
            version="1.0.0",
        )
        await repo.create(
            workspace_id=workspace.id,
            name="Design Helper",
            description="Helps with design",
            author="Author",
            category="design",
            version="1.0.0",
        )

        results = await repo.search("Reviewer")
        assert len(results) == 1
        assert results[0].name == "Code Reviewer Pro"

    async def test_search_by_description(
        self,
        repo: SkillMarketplaceListingRepository,
        workspace: Workspace,
    ) -> None:
        """Search matches description text too."""
        await repo.create(
            workspace_id=workspace.id,
            name="My Skill",
            description="Automated testing assistant",
            author="Author",
            category="testing",
            version="1.0.0",
        )

        results = await repo.search("testing assistant")
        assert len(results) == 1

    async def test_search_with_category_filter(
        self,
        repo: SkillMarketplaceListingRepository,
        workspace: Workspace,
    ) -> None:
        """Search with category filter narrows results."""
        await repo.create(
            workspace_id=workspace.id,
            name="Code Tool",
            description="A tool for coding",
            author="Author",
            category="development",
            version="1.0.0",
        )
        await repo.create(
            workspace_id=workspace.id,
            name="Design Tool",
            description="A tool for design",
            author="Author",
            category="design",
            version="1.0.0",
        )

        results = await repo.search("Tool", category="design")
        assert len(results) == 1
        assert results[0].name == "Design Tool"


class TestIncrementDownloadCount:
    """Tests for increment_download_count()."""

    async def test_increment(
        self,
        repo: SkillMarketplaceListingRepository,
        workspace: Workspace,
    ) -> None:
        """Download count increments by 1."""
        listing = await repo.create(
            workspace_id=workspace.id,
            name="Popular Skill",
            description="Very popular",
            author="Author",
            category="general",
            version="1.0.0",
        )
        assert listing.download_count == 0

        updated = await repo.increment_download_count(listing.id)
        assert updated is not None
        assert updated.download_count == 1

    async def test_increment_nonexistent_returns_none(
        self,
        repo: SkillMarketplaceListingRepository,
    ) -> None:
        """Incrementing non-existent listing returns None."""
        result = await repo.increment_download_count(uuid4())
        assert result is None


class TestUpdateAvgRating:
    """Tests for update_avg_rating()."""

    async def test_update_rating(
        self,
        repo: SkillMarketplaceListingRepository,
        workspace: Workspace,
    ) -> None:
        """Update avg_rating and verify."""
        listing = await repo.create(
            workspace_id=workspace.id,
            name="Rated Skill",
            description="Has ratings",
            author="Author",
            category="general",
            version="1.0.0",
        )
        assert listing.avg_rating is None

        updated = await repo.update_avg_rating(listing.id, 4.5)
        assert updated is not None
        assert updated.avg_rating == 4.5
