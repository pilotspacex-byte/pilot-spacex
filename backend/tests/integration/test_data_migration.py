"""Integration tests for memory_entries → graph_nodes data migration.

Verifies that migration 056_migrate_memory_to_graph correctly copies
rows from memory_entries to graph_nodes with the right node_type mapping and
that expired/deleted rows are excluded.

These tests require a real PostgreSQL instance (TEST_DATABASE_URL env var).
They are skipped on SQLite because the migration uses PostgreSQL-specific
functions (gen_random_uuid, jsonb_build_object).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Skip the entire module if no PostgreSQL URL is configured
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — migration tests require PostgreSQL",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _insert_memory_entry(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    content: str,
    source_type: str,
    source_id: uuid.UUID | None = None,
    pinned: bool = False,
    is_deleted: bool = False,
    expires_at: datetime | None = None,
) -> uuid.UUID:
    """Insert a raw memory_entries row and return its id."""
    entry_id = uuid.uuid4()
    now = datetime.now(UTC)
    await session.execute(
        text(
            """
        INSERT INTO memory_entries (
            id, workspace_id, content, source_type, source_id,
            pinned, is_deleted, expires_at, created_at, updated_at
        ) VALUES (
            :id, :workspace_id, :content, :source_type::memory_source_type_enum,
            :source_id, :pinned, :is_deleted, :expires_at, :created_at, :updated_at
        )
        """
        ),
        {
            "id": str(entry_id),
            "workspace_id": str(workspace_id),
            "content": content,
            "source_type": source_type,
            "source_id": str(source_id) if source_id else None,
            "pinned": pinned,
            "is_deleted": is_deleted,
            "expires_at": expires_at,
            "created_at": now,
            "updated_at": now,
        },
    )
    return entry_id


async def _run_migration_sql(session: AsyncSession) -> None:
    """Execute the upgrade SQL from migration 056 against the current session."""
    await session.execute(
        text(
            """
        INSERT INTO graph_nodes (
            id, workspace_id, user_id, node_type, external_id, label,
            content, properties, embedding, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            me.workspace_id,
            NULL,
            CASE me.source_type
                WHEN 'intent'        THEN 'work_intent'
                WHEN 'skill_outcome' THEN 'skill_outcome'
                WHEN 'user_feedback' THEN 'learned_pattern'
                WHEN 'constitution'  THEN 'constitution_rule'
                ELSE                      'skill_outcome'
            END,
            me.source_id,
            LEFT(me.content, 100),
            me.content,
            jsonb_build_object(
                'migrated_from', 'memory_entries',
                'source_type',   me.source_type::text,
                'pinned',        me.pinned
            ),
            NULL,
            me.created_at,
            COALESCE(me.updated_at, me.created_at)
        FROM memory_entries me
        WHERE
            me.is_deleted = FALSE
            AND (me.expires_at IS NULL OR me.expires_at > NOW())
        """
        )
    )


async def _run_downgrade_sql(session: AsyncSession) -> None:
    """Execute the downgrade SQL from migration 056 against the current session."""
    await session.execute(
        text(
            """
        DELETE FROM graph_nodes
        WHERE properties->>'migrated_from' = 'memory_entries'
        """
        )
    )


async def _count_graph_nodes(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    node_type: str,
) -> int:
    result = await session.execute(
        text(
            """
        SELECT COUNT(*) FROM graph_nodes
        WHERE workspace_id = :workspace_id
          AND node_type    = :node_type
          AND properties->>'migrated_from' = 'memory_entries'
        """
        ),
        {"workspace_id": str(workspace_id), "node_type": node_type},
    )
    return int(result.scalar_one())


# ---------------------------------------------------------------------------
# Test workspace setup
# ---------------------------------------------------------------------------


@pytest.fixture
async def migration_workspace(db_session_committed: AsyncSession) -> uuid.UUID:
    """Insert a minimal workspace row for migration tests and return its id."""
    wid = uuid.uuid4()
    await db_session_committed.execute(
        text(
            """
        INSERT INTO workspaces (id, name, slug, owner_id, created_at, updated_at)
        VALUES (:id, :name, :slug, :owner_id, NOW(), NOW())
        """
        ),
        {
            "id": str(wid),
            "name": "Migration Test Workspace",
            "slug": f"migration-test-{wid.hex[:8]}",
            "owner_id": str(uuid.uuid4()),
        },
    )
    await db_session_committed.commit()
    return wid


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skill_outcome_migrates_to_graph_node(
    db_session_committed: AsyncSession,
    migration_workspace: uuid.UUID,
) -> None:
    """memory_entries SKILL_OUTCOME rows appear in graph_nodes after migration."""
    content = "Resolved PS-42 by implementing retry logic in the job worker."
    source_id = uuid.uuid4()

    await _insert_memory_entry(
        db_session_committed,
        workspace_id=migration_workspace,
        content=content,
        source_type="skill_outcome",
        source_id=source_id,
        pinned=True,
    )
    await db_session_committed.commit()

    await _run_migration_sql(db_session_committed)
    await db_session_committed.commit()

    count = await _count_graph_nodes(
        db_session_committed, migration_workspace, "skill_outcome"
    )
    assert count == 1

    result = await db_session_committed.execute(
        text(
            """
        SELECT label, content, external_id, properties
        FROM graph_nodes
        WHERE workspace_id = :wid
          AND node_type = 'skill_outcome'
          AND properties->>'migrated_from' = 'memory_entries'
        LIMIT 1
        """
        ),
        {"wid": str(migration_workspace)},
    )
    row = result.mappings().one()

    assert row["content"] == content
    assert row["label"] == content[:100]
    assert str(row["external_id"]) == str(source_id)
    assert row["properties"]["source_type"] == "skill_outcome"
    assert row["properties"]["pinned"] is True
    assert row["properties"]["migrated_from"] == "memory_entries"


@pytest.mark.asyncio
async def test_intent_migrates_to_work_intent_node(
    db_session_committed: AsyncSession,
    migration_workspace: uuid.UUID,
) -> None:
    """memory_entries INTENT rows are mapped to node_type 'work_intent'."""
    content = "Implement knowledge graph search endpoint with hybrid scoring."

    await _insert_memory_entry(
        db_session_committed,
        workspace_id=migration_workspace,
        content=content,
        source_type="intent",
    )
    await db_session_committed.commit()

    await _run_migration_sql(db_session_committed)
    await db_session_committed.commit()

    count = await _count_graph_nodes(
        db_session_committed, migration_workspace, "work_intent"
    )
    assert count == 1


@pytest.mark.asyncio
async def test_user_feedback_migrates_to_learned_pattern(
    db_session_committed: AsyncSession,
    migration_workspace: uuid.UUID,
) -> None:
    """USER_FEEDBACK rows map to node_type 'learned_pattern'."""
    await _insert_memory_entry(
        db_session_committed,
        workspace_id=migration_workspace,
        content="User prefers concise PR descriptions without bullet-point lists.",
        source_type="user_feedback",
    )
    await db_session_committed.commit()

    await _run_migration_sql(db_session_committed)
    await db_session_committed.commit()

    count = await _count_graph_nodes(
        db_session_committed, migration_workspace, "learned_pattern"
    )
    assert count == 1


@pytest.mark.asyncio
async def test_constitution_migrates_to_constitution_rule(
    db_session_committed: AsyncSession,
    migration_workspace: uuid.UUID,
) -> None:
    """CONSTITUTION rows map to node_type 'constitution_rule'."""
    await _insert_memory_entry(
        db_session_committed,
        workspace_id=migration_workspace,
        content="MUST NOT expose PII in AI generated summaries.",
        source_type="constitution",
    )
    await db_session_committed.commit()

    await _run_migration_sql(db_session_committed)
    await db_session_committed.commit()

    count = await _count_graph_nodes(
        db_session_committed, migration_workspace, "constitution_rule"
    )
    assert count == 1


@pytest.mark.asyncio
async def test_expired_entries_not_migrated(
    db_session_committed: AsyncSession,
    migration_workspace: uuid.UUID,
) -> None:
    """Expired memory entries are excluded from the migration."""
    past = datetime.now(UTC) - timedelta(hours=1)

    await _insert_memory_entry(
        db_session_committed,
        workspace_id=migration_workspace,
        content="This entry expired an hour ago.",
        source_type="skill_outcome",
        expires_at=past,
    )
    # Also insert a non-expired entry to confirm it IS migrated
    await _insert_memory_entry(
        db_session_committed,
        workspace_id=migration_workspace,
        content="This entry has no expiry — must be migrated.",
        source_type="skill_outcome",
    )
    await db_session_committed.commit()

    await _run_migration_sql(db_session_committed)
    await db_session_committed.commit()

    count = await _count_graph_nodes(
        db_session_committed, migration_workspace, "skill_outcome"
    )
    assert count == 1  # only the non-expired row


@pytest.mark.asyncio
async def test_deleted_entries_not_migrated(
    db_session_committed: AsyncSession,
    migration_workspace: uuid.UUID,
) -> None:
    """Soft-deleted memory entries are excluded from the migration."""
    await _insert_memory_entry(
        db_session_committed,
        workspace_id=migration_workspace,
        content="This entry is soft-deleted and must not be migrated.",
        source_type="skill_outcome",
        is_deleted=True,
    )
    await db_session_committed.commit()

    await _run_migration_sql(db_session_committed)
    await db_session_committed.commit()

    count = await _count_graph_nodes(
        db_session_committed, migration_workspace, "skill_outcome"
    )
    assert count == 0


@pytest.mark.asyncio
async def test_label_truncated_to_100_chars(
    db_session_committed: AsyncSession,
    migration_workspace: uuid.UUID,
) -> None:
    """label column is truncated to 100 characters from content."""
    long_content = "A" * 250

    await _insert_memory_entry(
        db_session_committed,
        workspace_id=migration_workspace,
        content=long_content,
        source_type="skill_outcome",
    )
    await db_session_committed.commit()

    await _run_migration_sql(db_session_committed)
    await db_session_committed.commit()

    result = await db_session_committed.execute(
        text(
            """
        SELECT label FROM graph_nodes
        WHERE workspace_id = :wid
          AND node_type = 'skill_outcome'
          AND properties->>'migrated_from' = 'memory_entries'
        LIMIT 1
        """
        ),
        {"wid": str(migration_workspace)},
    )
    label = result.scalar_one()
    assert len(label) == 100


@pytest.mark.asyncio
async def test_embedding_not_migrated(
    db_session_committed: AsyncSession,
    migration_workspace: uuid.UUID,
) -> None:
    """Embedding column is NULL on migrated nodes (768-dim Gemini incompatible)."""
    await _insert_memory_entry(
        db_session_committed,
        workspace_id=migration_workspace,
        content="Node with original embedding that must not be copied.",
        source_type="skill_outcome",
    )
    await db_session_committed.commit()

    await _run_migration_sql(db_session_committed)
    await db_session_committed.commit()

    result = await db_session_committed.execute(
        text(
            """
        SELECT embedding FROM graph_nodes
        WHERE workspace_id = :wid
          AND node_type = 'skill_outcome'
          AND properties->>'migrated_from' = 'memory_entries'
        LIMIT 1
        """
        ),
        {"wid": str(migration_workspace)},
    )
    embedding = result.scalar_one()
    assert embedding is None


@pytest.mark.asyncio
async def test_migration_downgrade_cleans_up(
    db_session_committed: AsyncSession,
    migration_workspace: uuid.UUID,
) -> None:
    """Downgrade removes exactly the rows inserted by the migration."""
    await _insert_memory_entry(
        db_session_committed,
        workspace_id=migration_workspace,
        content="Row that will be removed by downgrade.",
        source_type="skill_outcome",
    )
    await db_session_committed.commit()

    await _run_migration_sql(db_session_committed)
    await db_session_committed.commit()

    # Confirm row exists before downgrade
    pre_count = await _count_graph_nodes(
        db_session_committed, migration_workspace, "skill_outcome"
    )
    assert pre_count == 1

    await _run_downgrade_sql(db_session_committed)
    await db_session_committed.commit()

    post_count = await _count_graph_nodes(
        db_session_committed, migration_workspace, "skill_outcome"
    )
    assert post_count == 0
