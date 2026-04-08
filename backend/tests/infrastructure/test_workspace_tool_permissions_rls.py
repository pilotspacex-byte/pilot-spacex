"""RLS isolation test for Phase 69 tool-permission tables.

Phase 69 Wave 1 (PERM-01, PERM-06). Verifies:

1. A workspace member can only SELECT workspace_tool_permissions rows
   belonging to workspaces they are a member of.
2. A workspace member cannot INSERT a row for a workspace they do not
   administer (RLS admin_write policy kicks in).
3. The DB layer accepts mode='auto' for any tool — DD-003 enforcement
   for destructive tools lives in the service layer (Wave 2), not in
   a DB-level CHECK. This test pins that invariant so a future CHECK
   addition is a deliberate change, not an accident.

These tests require a real PostgreSQL instance with Phase 69 migrations
applied. They skip cleanly when ``TEST_DATABASE_URL`` is unset (the
default SQLite test engine silently no-ops RLS — see
``.claude/rules/testing.md``).
"""

from __future__ import annotations

import os
import subprocess
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from pilot_space.infrastructure.database.rls import set_rls_context


def _require_test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "requires TEST_DATABASE_URL pointing at a real postgres instance "
            "(RLS tests cannot run under SQLite)",
            allow_module_level=False,
        )
    return url


@pytest.fixture(scope="module")
def pg_engine() -> AsyncEngine:
    """Async engine targeting ``TEST_DATABASE_URL`` with migrations applied."""
    url = _require_test_database_url()
    backend_dir = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        check=True,
    )
    return create_async_engine(url, future=True)


@pytest_asyncio.fixture
async def pg_session(pg_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Function-scoped async session with transactional rollback."""
    async with pg_engine.connect() as connection:
        transaction = await connection.begin()
        factory = async_sessionmaker(bind=connection, expire_on_commit=False)
        async with factory() as session:
            try:
                yield session
            finally:
                await transaction.rollback()


async def _seed_workspace_and_admin(
    session: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert one workspace and one OWNER member; return (workspace_id, user_id)."""
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    slug = f"ws-{workspace_id.hex[:8]}"

    # users.id has FK from workspace_members; insert the user via the base
    # users table. The users table uses RLS but with service_role bypass,
    # and our connection is the DB owner which bypasses RLS by default
    # unless FORCE ROW LEVEL SECURITY is set. set_config role to service_role
    # to stay inside the bypass policy explicitly.
    await session.execute(text("SELECT set_config('role', 'service_role', true)"))

    await session.execute(
        text(
            """
            INSERT INTO users (id, email, full_name, created_at, updated_at)
            VALUES (:id, :email, :name, now(), now())
            """
        ),
        {"id": str(user_id), "email": f"{user_id.hex[:8]}@example.test", "name": "Test"},
    )
    await session.execute(
        text(
            """
            INSERT INTO workspaces (id, name, slug, created_at, updated_at)
            VALUES (:id, :name, :slug, now(), now())
            """
        ),
        {"id": str(workspace_id), "name": slug, "slug": slug},
    )
    await session.execute(
        text(
            """
            INSERT INTO workspace_members
                (id, workspace_id, user_id, role, is_deleted, created_at, updated_at)
            VALUES
                (gen_random_uuid(), :ws, :u, 'OWNER', false, now(), now())
            """
        ),
        {"ws": str(workspace_id), "u": str(user_id)},
    )
    return workspace_id, user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workspace_tool_permissions_rls_isolation(
    pg_session: AsyncSession,
) -> None:
    """User A sees only workspace A's permissions, not workspace B's."""
    ws_a, user_a = await _seed_workspace_and_admin(pg_session)
    ws_b, _user_b = await _seed_workspace_and_admin(pg_session)

    # Seed one permission per workspace under service_role bypass.
    await pg_session.execute(text("SELECT set_config('role', 'service_role', true)"))
    for ws, actor in ((ws_a, user_a), (ws_b, _user_b)):
        await pg_session.execute(
            text(
                """
                INSERT INTO workspace_tool_permissions
                    (id, workspace_id, tool_name, mode, updated_by, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), :ws, 'update_note', 'ask', :u, now(), now())
                """
            ),
            {"ws": str(ws), "u": str(actor)},
        )

    # Drop back to authenticated role and set RLS context to user A.
    await pg_session.execute(text("SELECT set_config('role', 'authenticated', true)"))
    await set_rls_context(pg_session, user_id=user_a)

    result = await pg_session.execute(
        text("SELECT workspace_id FROM workspace_tool_permissions")
    )
    visible = {row[0] for row in result.fetchall()}
    assert ws_a in visible
    assert ws_b not in visible


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workspace_tool_permissions_rls_blocks_cross_workspace_insert(
    pg_session: AsyncSession,
) -> None:
    """User A cannot INSERT a permission row for workspace B."""
    ws_a, user_a = await _seed_workspace_and_admin(pg_session)
    ws_b, _user_b = await _seed_workspace_and_admin(pg_session)

    await pg_session.execute(text("SELECT set_config('role', 'authenticated', true)"))
    await set_rls_context(pg_session, user_id=user_a)

    with pytest.raises((DBAPIError, ProgrammingError)):
        await pg_session.execute(
            text(
                """
                INSERT INTO workspace_tool_permissions
                    (id, workspace_id, tool_name, mode, updated_by, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), :ws, 'delete_issue', 'ask', :u, now(), now())
                """
            ),
            {"ws": str(ws_b), "u": str(user_a)},
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workspace_tool_permissions_allows_auto_for_destructive_tool_at_db_layer(
    pg_session: AsyncSession,
) -> None:
    """DD-003 is enforced in the service layer, not the DB.

    Pin the invariant: the DB will happily accept mode='auto' even for a
    destructive tool name. Wave 2 adds service-layer validation; if a
    future migration adds a DB-level CHECK, this test must be updated
    deliberately.
    """
    ws_a, user_a = await _seed_workspace_and_admin(pg_session)

    await pg_session.execute(text("SELECT set_config('role', 'service_role', true)"))
    await pg_session.execute(
        text(
            """
            INSERT INTO workspace_tool_permissions
                (id, workspace_id, tool_name, mode, updated_by, created_at, updated_at)
            VALUES
                (gen_random_uuid(), :ws, 'delete_issue', 'auto', :u, now(), now())
            """
        ),
        {"ws": str(ws_a), "u": str(user_a)},
    )

    result = await pg_session.execute(
        text(
            "SELECT mode FROM workspace_tool_permissions "
            "WHERE workspace_id = :ws AND tool_name = 'delete_issue'"
        ),
        {"ws": str(ws_a)},
    )
    assert result.scalar_one() == "auto"
