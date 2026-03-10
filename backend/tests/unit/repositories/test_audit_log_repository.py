"""Tests for AuditLogRepository actor_type filter.

Phase 4 — AI Governance (AIGOV-03):
AuditLogRepository.list_filtered() and list_for_export() must support
filtering by actor_type (AI | USER) to enable AI-specific audit views.

Implemented in plan 04-03 (AIGOV-03 audit log actor_type filter).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from pilot_space.infrastructure.database.base import Base
from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog
from pilot_space.infrastructure.database.repositories.audit_log_repository import (
    AuditLogRepository,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Scoped fixtures — only create audit_log table (avoids PostgreSQL-specific
# server_defaults in chat_attachments and other models)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def audit_engine():
    """Create an in-memory SQLite engine with only the audit_log table."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        # Only create the audit_log table — avoids PG-specific server_defaults
        await conn.run_sync(
            lambda sync_conn: Base.metadata.tables["audit_log"].create(sync_conn, checkfirst=True)
        )
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.tables["audit_log"].drop(sync_conn, checkfirst=True)
        )
    await engine.dispose()


@pytest_asyncio.fixture
async def audit_session(audit_engine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test session wrapping audit_engine with rollback."""
    session_factory = async_sessionmaker(
        audit_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session, session.begin():
        yield session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_audit_row(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    actor_type: ActorType,
    action: str = "issue.create",
) -> AuditLog:
    """Insert a minimal AuditLog row directly into the session."""
    row = AuditLog(
        workspace_id=workspace_id,
        actor_id=uuid.uuid4(),
        actor_type=actor_type,
        action=action,
        resource_type="issue",
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_list_filtered_actor_type_ai(audit_session: AsyncSession) -> None:
    """actor_type=AI filter returns only rows where actor_type=AI."""
    workspace_id = uuid.uuid4()

    ai_row = await _create_audit_row(audit_session, workspace_id, ActorType.AI)
    _user_row = await _create_audit_row(audit_session, workspace_id, ActorType.USER)

    repo = AuditLogRepository(audit_session)
    page = await repo.list_filtered(
        workspace_id=workspace_id,
        actor_type=ActorType.AI,
    )

    assert len(page.items) == 1
    assert page.items[0].id == ai_row.id
    assert page.items[0].actor_type == ActorType.AI


async def test_list_filtered_actor_type_user(audit_session: AsyncSession) -> None:
    """actor_type=USER filter excludes AI rows."""
    workspace_id = uuid.uuid4()

    _ai_row = await _create_audit_row(audit_session, workspace_id, ActorType.AI)
    user_row = await _create_audit_row(audit_session, workspace_id, ActorType.USER)

    repo = AuditLogRepository(audit_session)
    page = await repo.list_filtered(
        workspace_id=workspace_id,
        actor_type=ActorType.USER,
    )

    assert len(page.items) == 1
    assert page.items[0].id == user_row.id
    assert page.items[0].actor_type == ActorType.USER


async def test_list_for_export_actor_type_filter(audit_session: AsyncSession) -> None:
    """list_for_export with actor_type=AI yields only AI-generated audit entries."""
    workspace_id = uuid.uuid4()

    ai_row = await _create_audit_row(audit_session, workspace_id, ActorType.AI)
    _user_row = await _create_audit_row(audit_session, workspace_id, ActorType.USER)

    repo = AuditLogRepository(audit_session)
    rows = await repo.list_for_export(
        workspace_id=workspace_id,
        actor_type=ActorType.AI,
    )

    assert len(rows) == 1
    assert rows[0].id == ai_row.id
    assert rows[0].actor_type == ActorType.AI


async def test_list_filtered_no_actor_type(audit_session: AsyncSession) -> None:
    """Omitting actor_type returns all rows (no filter applied)."""
    workspace_id = uuid.uuid4()

    await _create_audit_row(audit_session, workspace_id, ActorType.AI)
    await _create_audit_row(audit_session, workspace_id, ActorType.USER)
    await _create_audit_row(audit_session, workspace_id, ActorType.SYSTEM)

    repo = AuditLogRepository(audit_session)
    page = await repo.list_filtered(workspace_id=workspace_id)

    assert len(page.items) == 3
