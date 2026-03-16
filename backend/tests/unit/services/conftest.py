"""Local conftest for unit/services tests.

Uses raw SQLite DDL to create tables, avoiding PostgreSQL-specific syntax
(gen_random_uuid, char_length, ::jsonb) that breaks on SQLite.
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
    # Simplified sequence function — returns 1 for unit tests (no race conditions)
    dbapi_conn.create_function("get_next_issue_sequence", 1, lambda _project_id: 1)
    # Allow UUID objects as parameters by registering an adapter
    import sqlite3

    sqlite3.register_adapter(uuid.UUID, str)


_CREATE_TABLES_SQL = """
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
    settings TEXT,
    audit_retention_days INTEGER DEFAULT 90,
    rate_limit_standard_rpm INTEGER DEFAULT 60,
    rate_limit_ai_rpm INTEGER DEFAULT 20,
    storage_quota_mb INTEGER DEFAULT 5120,
    storage_used_bytes INTEGER DEFAULT 0,
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
    weekly_available_hours REAL NOT NULL DEFAULT 40.0,
    custom_role_id TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME,
    UNIQUE(user_id, workspace_id)
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    identifier TEXT NOT NULL,
    icon TEXT,
    settings TEXT,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    lead_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    default_assignee_id TEXT,
    network TEXT NOT NULL DEFAULT '2',
    emoji TEXT,
    icon_prop TEXT,
    cover_image TEXT,
    sort_order REAL DEFAULT 65535,
    estimate_type TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT '',
    description TEXT,
    content TEXT,
    category TEXT,
    is_default BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS states (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#94a3b8',
    "group" TEXT NOT NULL DEFAULT 'unstarted',
    sequence INTEGER DEFAULT 0,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    project_id TEXT REFERENCES projects(id),
    owner_id TEXT REFERENCES users(id),
    title TEXT NOT NULL DEFAULT '',
    content TEXT,
    summary TEXT,
    word_count INTEGER DEFAULT 0,
    reading_time_mins INTEGER DEFAULT 0,
    parent_id TEXT REFERENCES notes(id) ON DELETE SET NULL,
    depth INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL DEFAULT 0,
    is_pinned BOOLEAN DEFAULT 0,
    is_guided_template BOOLEAN DEFAULT 0,
    template_id TEXT,
    source_chat_session_id TEXT,
    last_edited_by_id TEXT,
    icon_emoji TEXT,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS note_annotations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    block_id TEXT,
    type TEXT,
    content TEXT,
    confidence REAL,
    status TEXT,
    ai_metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS threaded_discussions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    note_id TEXT REFERENCES notes(id) ON DELETE CASCADE,
    block_id TEXT,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    target_type TEXT NOT NULL DEFAULT 'note',
    target_id TEXT,
    resolved_by_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS issues (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT,
    title TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT '',
    description TEXT,
    description_html TEXT,
    state_id TEXT,
    priority TEXT DEFAULT 'none',
    sequence_id INTEGER,
    assignee_id TEXT,
    reporter_id TEXT,
    cycle_id TEXT,
    module_id TEXT,
    parent_id TEXT,
    estimate_points REAL,
    estimate_hours REAL,
    start_date DATETIME,
    target_date DATETIME,
    sort_order REAL DEFAULT 0,
    ai_metadata TEXT DEFAULT '{}',
    acceptance_criteria TEXT,
    technical_requirements TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS cycles (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    start_date DATETIME,
    end_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS modules (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'backlog',
    start_date DATETIME,
    target_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS labels (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#6b7280',
    description TEXT,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS issue_labels (
    issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    label_id TEXT NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (issue_id, label_id)
);

CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    issue_id TEXT REFERENCES issues(id) ON DELETE CASCADE,
    actor_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    verb TEXT NOT NULL,
    field TEXT,
    old_value TEXT,
    new_value TEXT,
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    acceptance_criteria TEXT,
    status TEXT NOT NULL DEFAULT 'todo',
    sort_order INTEGER NOT NULL DEFAULT 0,
    estimated_hours REAL,
    code_references TEXT,
    ai_prompt TEXT,
    ai_generated BOOLEAN NOT NULL DEFAULT 0,
    dependency_ids TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS ai_contexts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    issue_id TEXT NOT NULL UNIQUE REFERENCES issues(id) ON DELETE CASCADE,
    content TEXT NOT NULL DEFAULT '{}',
    claude_code_prompt TEXT,
    related_issues TEXT NOT NULL DEFAULT '[]',
    related_notes TEXT NOT NULL DEFAULT '[]',
    related_pages TEXT NOT NULL DEFAULT '[]',
    code_references TEXT NOT NULL DEFAULT '[]',
    tasks_checklist TEXT NOT NULL DEFAULT '[]',
    conversation_history TEXT NOT NULL DEFAULT '[]',
    generated_at DATETIME,
    last_refined_at DATETIME,
    version INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    actor_id TEXT,
    actor_type TEXT,
    action TEXT,
    resource_type TEXT,
    resource_id TEXT,
    payload TEXT,
    ai_input TEXT,
    ai_output TEXT,
    ai_model TEXT,
    ai_token_cost REAL,
    ai_rationale TEXT,
    ip_address TEXT,
    workspace_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS note_issue_links (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    link_type TEXT NOT NULL DEFAULT 'reference',
    block_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS note_note_links (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    source_note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    target_note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS ai_configurations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    api_key_encrypted TEXT,
    is_active BOOLEAN DEFAULT 1 NOT NULL,
    config TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS workspace_api_keys (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1 NOT NULL,
    created_by TEXT REFERENCES users(id),
    expires_at DATETIME,
    last_used_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS ai_approval_requests (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    session_id TEXT,
    tool_name TEXT NOT NULL,
    tool_input TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    decided_by TEXT,
    decided_at DATETIME,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS ai_cost_records (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cached_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,
    session_id TEXT,
    user_id TEXT,
    operation TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS ai_sessions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    title TEXT,
    agent_type TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    metadata_json TEXT,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS role_templates (
    id TEXT PRIMARY KEY,
    role_type TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL,
    default_skill_content TEXT NOT NULL,
    icon TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
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
    UNIQUE(user_id, workspace_id, role_type)
);
"""


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create SQLite engine with raw DDL for service tests.

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
        autoflush=False,
    )

    async with session_factory() as session, session.begin():
        yield session
