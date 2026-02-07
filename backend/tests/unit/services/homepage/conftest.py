"""Local conftest for homepage service tests.

Adds SQLite DDL for homepage-specific tables on top of the parent conftest.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool


def _register_sqlite_functions(dbapi_conn, connection_record) -> None:
    """Register PostgreSQL-compatible functions for SQLite."""
    dbapi_conn.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))
    dbapi_conn.create_function("char_length", 1, lambda s: len(s) if s else 0)


_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    default_sdlc_role TEXT,
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
    settings TEXT,
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
    role TEXT NOT NULL DEFAULT 'member',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME,
    UNIQUE(user_id, workspace_id)
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    identifier TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    settings TEXT,
    lead_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    word_count INTEGER DEFAULT 0,
    reading_time_mins INTEGER DEFAULT 0,
    is_pinned BOOLEAN DEFAULT 0 NOT NULL,
    is_guided_template BOOLEAN DEFAULT 0 NOT NULL,
    template_id TEXT,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    source_chat_session_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS note_annotations (
    id TEXT PRIMARY KEY,
    note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    block_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL DEFAULT 0.8,
    status TEXT NOT NULL DEFAULT 'pending',
    created_by TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS states (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    "group" TEXT NOT NULL,
    sequence INTEGER DEFAULT 0,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS issues (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    sequence_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    description_html TEXT,
    priority TEXT NOT NULL DEFAULT 'none',
    state_id TEXT REFERENCES states(id) ON DELETE SET NULL,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    assignee_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    reporter_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    cycle_id TEXT,
    module_id TEXT,
    parent_id TEXT,
    estimate_points REAL,
    start_date DATETIME,
    target_date DATETIME,
    sort_order REAL DEFAULT 65535,
    ai_metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    issue_id TEXT REFERENCES issues(id) ON DELETE CASCADE,
    actor_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    activity_type TEXT NOT NULL,
    comment TEXT,
    field TEXT,
    old_value TEXT,
    new_value TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS workspace_digests (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    generated_by TEXT NOT NULL DEFAULT 'scheduled',
    suggestions TEXT NOT NULL DEFAULT '[]',
    model_used TEXT,
    token_usage TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS digest_dismissals (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    suggestion_category TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    dismissed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS ai_sessions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    context_id TEXT,
    title TEXT,
    session_data TEXT NOT NULL DEFAULT '{}',
    total_cost_usd REAL DEFAULT 0,
    turn_count INTEGER DEFAULT 0,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES ai_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS cycles (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active',
    start_date DATETIME,
    end_date DATETIME,
    sequence INTEGER DEFAULT 0,
    owned_by_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);
"""


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create SQLite engine with raw DDL for homepage service tests.

    Uses raw SQL DDL to avoid PostgreSQL-specific syntax from SQLAlchemy models.
    Registers ``gen_random_uuid`` and ``char_length`` as SQLite UDFs.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    event.listen(engine.sync_engine, "connect", _register_sqlite_functions)

    async with engine.begin() as conn:
        for raw_stmt in _CREATE_TABLES_SQL.strip().split(";"):
            cleaned = raw_stmt.strip()
            if cleaned:
                await conn.execute(text(cleaned))

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create database session with transaction rollback.

    Overrides root conftest to use the local SQLite test engine.
    """
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
    )

    async with session_factory() as session, session.begin():
        yield session
        await session.rollback()


@pytest.fixture
def workspace_id() -> uuid.UUID:
    """Generate a workspace UUID for tests."""
    return uuid.uuid4()


@pytest.fixture
def user_id() -> uuid.UUID:
    """Generate a user UUID for tests."""
    return uuid.uuid4()


@pytest.fixture
async def _seed_workspace(
    db_session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Seed database with user, workspace, and workspace_member using raw SQL.

    Args:
        db_session: The database session.
        workspace_id: Workspace UUID to create.
        user_id: User UUID to create.
    """
    # Use raw SQL to avoid relationship loading issues
    await db_session.execute(
        text(
            """
            INSERT INTO users (id, email, full_name, created_at, updated_at, is_deleted)
            VALUES (:user_id, :email, :full_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)
            """
        ),
        {
            "user_id": str(user_id),
            "email": f"test-{user_id}@example.com",
            "full_name": "Test User",
        },
    )

    await db_session.execute(
        text(
            """
            INSERT INTO workspaces (id, name, slug, owner_id, created_at, updated_at, is_deleted)
            VALUES (:workspace_id, :name, :slug, :owner_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)
            """
        ),
        {
            "workspace_id": str(workspace_id),
            "name": "Test Workspace",
            "slug": f"test-{workspace_id}",
            "owner_id": str(user_id),
        },
    )

    await db_session.execute(
        text(
            """
            INSERT INTO workspace_members (id, user_id, workspace_id, role, created_at, updated_at, is_deleted)
            VALUES (:id, :user_id, :workspace_id, :role, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "user_id": str(user_id),
            "workspace_id": str(workspace_id),
            "role": "owner",
        },
    )

    await db_session.flush()
