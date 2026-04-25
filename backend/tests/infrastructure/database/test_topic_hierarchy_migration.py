"""Migration 112 smoke tests — topic nested hierarchy schema.

Verifies the additive schema landed by ``112_topic_nested_hierarchy``:

  * ``notes.parent_topic_id`` column exists (UUID nullable self-FK)
  * ``notes.topic_depth`` column exists (SmallInteger not null, default 0)
  * ``idx_notes_parent_topic_id`` and ``idx_notes_workspace_parent`` indexes
  * Existing page-hierarchy columns (``parent_id`` / ``depth`` / ``position``)
    are still present (regression guard against accidental edit)

RLS preservation is asserted only when ``TEST_DATABASE_URL`` points at a
PostgreSQL instance — SQLite doesn't have ``pg_policies``.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import inspect

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


pytestmark = pytest.mark.asyncio


async def test_migration_112_adds_parent_topic_id_column(test_engine: AsyncEngine) -> None:
    """`notes.parent_topic_id` column exists after migration 112."""

    def _columns(sync_conn: object) -> list[dict[str, object]]:
        return inspect(sync_conn).get_columns("notes")

    async with test_engine.connect() as conn:
        columns = await conn.run_sync(_columns)

    by_name = {c["name"]: c for c in columns}
    assert "parent_topic_id" in by_name, "parent_topic_id column missing"
    assert by_name["parent_topic_id"]["nullable"] is True


async def test_migration_112_adds_topic_depth_column(test_engine: AsyncEngine) -> None:
    """`notes.topic_depth` column exists, NOT NULL, with default 0."""

    def _columns(sync_conn: object) -> list[dict[str, object]]:
        return inspect(sync_conn).get_columns("notes")

    async with test_engine.connect() as conn:
        columns = await conn.run_sync(_columns)

    by_name = {c["name"]: c for c in columns}
    assert "topic_depth" in by_name, "topic_depth column missing"
    assert by_name["topic_depth"]["nullable"] is False


async def test_migration_112_creates_topic_indexes(test_engine: AsyncEngine) -> None:
    """Both topic-hierarchy indexes were created."""

    def _indexes(sync_conn: object) -> list[dict[str, object]]:
        return inspect(sync_conn).get_indexes("notes")

    async with test_engine.connect() as conn:
        indexes = await conn.run_sync(_indexes)

    names = {idx["name"] for idx in indexes}
    assert "idx_notes_parent_topic_id" in names, names
    assert "idx_notes_workspace_parent" in names, names


async def test_migration_112_preserves_page_hierarchy_columns(
    test_engine: AsyncEngine,
) -> None:
    """Page-level hierarchy columns (parent_id, depth, position) untouched.

    Regression guard: phase 93 introduces a SECOND hierarchy
    (parent_topic_id, topic_depth) and MUST NOT touch the existing
    page-level fields.
    """

    def _columns(sync_conn: object) -> list[dict[str, object]]:
        return inspect(sync_conn).get_columns("notes")

    async with test_engine.connect() as conn:
        columns = await conn.run_sync(_columns)

    names = {c["name"] for c in columns}
    for legacy in ("parent_id", "depth", "position"):
        assert legacy in names, f"page-hierarchy column {legacy!r} missing"


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="RLS preservation requires Postgres (pg_policies)",
)
async def test_migration_112_preserves_rls_policies(test_engine: AsyncEngine) -> None:
    """Existing notes RLS policy set is unchanged after migration 112.

    Skipped when the test DB is SQLite (no pg_policies). When running against
    Postgres, asserts the workspace_isolation + service_role policies on
    ``notes`` are still present (additive migration must not alter RLS).
    """
    from sqlalchemy import text

    async with test_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT policyname FROM pg_policies "
                "WHERE schemaname = 'public' AND tablename = 'notes'"
            )
        )
        policy_names = {row[0] for row in result.fetchall()}

    # The two canonical policies emitted by get_workspace_rls_policy_sql.
    assert any("workspace_isolation" in p for p in policy_names), policy_names
    assert any("service_role" in p for p in policy_names), policy_names


# ── ORM round-trip (Task 2 — model exposes parent_topic_id / topic_depth) ────


async def test_note_model_exposes_topic_hierarchy_fields() -> None:
    """Note ORM has parent_topic_id (UUID|None) and topic_depth (int) Mapped attrs."""
    from pilot_space.infrastructure.database.models.note import Note

    # Mapped attributes resolve via the declarative class, not the instance.
    assert hasattr(Note, "parent_topic_id")
    assert hasattr(Note, "topic_depth")

    # Page-level hierarchy still present (regression guard).
    assert hasattr(Note, "parent_id")
    assert hasattr(Note, "depth")
    assert hasattr(Note, "position")


async def test_note_model_persists_topic_hierarchy_defaults(
    db_session: object,  # AsyncSession; loose typing keeps file import-light
) -> None:
    """A freshly-inserted note rounds-trips with parent_topic_id=None, topic_depth=0."""
    from uuid import uuid4

    from pilot_space.infrastructure.database.models import (
        Note,
        User,
        Workspace,
    )

    workspace = Workspace(
        id=uuid4(), name="Topic Test WS", slug="topic-test-ws", owner_id=uuid4()
    )
    db_session.add(workspace)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]

    user = User(id=uuid4(), email="topic-default@example.com", full_name="Topic Default")
    db_session.add(user)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]

    note = Note(
        id=uuid4(),
        workspace_id=workspace.id,
        owner_id=user.id,
        title="Root topic",
        content={},
    )
    db_session.add(note)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]

    fetched = await db_session.get(Note, note.id)  # type: ignore[attr-defined]
    assert fetched is not None
    assert fetched.parent_topic_id is None
    assert fetched.topic_depth == 0


async def test_note_model_persists_topic_hierarchy_assignment(
    db_session: object,
) -> None:
    """Setting parent_topic_id and topic_depth round-trips through the ORM."""
    from uuid import uuid4

    from pilot_space.infrastructure.database.models import (
        Note,
        User,
        Workspace,
    )

    workspace = Workspace(
        id=uuid4(), name="Topic Assign WS", slug="topic-assign-ws", owner_id=uuid4()
    )
    db_session.add(workspace)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]

    user = User(id=uuid4(), email="topic-assign@example.com", full_name="Topic Assign")
    db_session.add(user)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]

    parent = Note(
        id=uuid4(),
        workspace_id=workspace.id,
        owner_id=user.id,
        title="Parent topic",
        content={},
    )
    db_session.add(parent)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]

    child = Note(
        id=uuid4(),
        workspace_id=workspace.id,
        owner_id=user.id,
        title="Child topic",
        content={},
        parent_topic_id=parent.id,
        topic_depth=1,
    )
    db_session.add(child)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]

    fetched = await db_session.get(Note, child.id)  # type: ignore[attr-defined]
    assert fetched is not None
    assert fetched.parent_topic_id == parent.id
    assert fetched.topic_depth == 1
