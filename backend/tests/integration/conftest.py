"""Integration test fixtures that require a real PostgreSQL instance.

Phase 69 Wave 0 adds pgvector + RLS smoke tests. The default test engine
is SQLite in-memory (see ``backend/tests/conftest.py``), which silently
no-ops RLS policies and does not support pgvector. These fixtures skip
cleanly when ``TEST_DATABASE_URL`` is unset so they never produce false
greens under the default SQLite engine.

See `.claude/rules/testing.md` for the rationale.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _require_test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "requires TEST_DATABASE_URL pointing at a real postgres instance "
            "(pgvector + RLS tests cannot run under SQLite)",
            allow_module_level=False,
        )
    return url


@pytest.fixture(scope="session")
def pg_engine() -> AsyncEngine:
    """Session-scoped async engine targeting ``TEST_DATABASE_URL``.

    Runs ``alembic upgrade head`` exactly once per session so pgvector
    extensions, RLS policies, and all Phase 69 migrations are in place.
    Skips cleanly when ``TEST_DATABASE_URL`` is unset.
    """
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
    """Function-scoped async session with transactional rollback.

    Any writes made inside the test are rolled back on teardown so tests
    stay hermetic even though the underlying engine is a real Postgres.
    """
    async with pg_engine.connect() as connection:
        transaction = await connection.begin()
        session_factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
        )
        async with session_factory() as session:
            try:
                yield session
            finally:
                await transaction.rollback()
