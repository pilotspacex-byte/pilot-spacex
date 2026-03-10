"""Unit tests for WorkIntentRepository and IntentArtifactRepository.

Uses isolated SQLite in-memory fixtures (raw DDL) to avoid PostgreSQL-specific
syntax in the shared conftest. Covers all custom query methods.

Feature 015: AI Workforce Platform
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

from pilot_space.domain.intent_artifact import ArtifactType
from pilot_space.domain.work_intent import (
    IntentStatus,
    WorkIntent as DomainWorkIntent,
)
from pilot_space.infrastructure.database.models import WorkIntent
from pilot_space.infrastructure.database.models.work_intent import (
    DedupStatus as DBDedupStatus,
    IntentArtifact,
    IntentStatus as DBIntentStatus,
)
from pilot_space.infrastructure.database.repositories.intent_artifact_repository import (
    IntentArtifactRepository,
)
from pilot_space.infrastructure.database.repositories.intent_repository import (
    WorkIntentRepository,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# SQLite schema (raw DDL — avoids PostgreSQL-specific ORM syntax)
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    owner_id TEXT,
    description TEXT,
    settings TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS work_intents (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    what TEXT NOT NULL,
    why TEXT,
    constraints TEXT,
    acceptance TEXT,
    status TEXT NOT NULL DEFAULT 'detected',
    dedup_status TEXT NOT NULL DEFAULT 'pending',
    owner TEXT,
    confidence REAL NOT NULL DEFAULT 0.5,
    parent_intent_id TEXT REFERENCES work_intents(id) ON DELETE SET NULL,
    source_block_id TEXT,
    embedding TEXT,
    dedup_hash TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS intent_artifacts (
    id TEXT PRIMARY KEY,
    intent_id TEXT NOT NULL REFERENCES work_intents(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    reference_id TEXT NOT NULL,
    reference_type TEXT NOT NULL,
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_work_intent(workspace_id: Any, **kwargs: Any) -> WorkIntent:
    """Create a WorkIntent model instance with sensible defaults."""
    what = kwargs.pop("what", "Build login page")
    defaults: dict[str, Any] = {
        "id": uuid4(),
        "workspace_id": workspace_id,
        "what": what,
        "confidence": 0.9,
        "status": DBIntentStatus.DETECTED,
        "dedup_status": DBDedupStatus.COMPLETE,
        "dedup_hash": DomainWorkIntent.compute_dedup_hash(what),
    }
    defaults.update(kwargs)
    return WorkIntent(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def workspace_id(db_session: AsyncSession) -> _uuid_mod.UUID:
    """Seed a workspace and return its UUID."""
    ws_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO workspaces (id, name, slug, owner_id) VALUES (:id, :name, :slug, :owner_id)"
        ),
        {
            "id": str(ws_id),
            "name": "Test WS",
            "slug": f"test-ws-{ws_id.hex[:6]}",
            "owner_id": str(uuid4()),
        },
    )
    await db_session.flush()
    return ws_id


@pytest.fixture
def intent_repo(db_session: AsyncSession) -> WorkIntentRepository:
    return WorkIntentRepository(session=db_session)


@pytest.fixture
def artifact_repo(db_session: AsyncSession) -> IntentArtifactRepository:
    return IntentArtifactRepository(session=db_session)


# ---------------------------------------------------------------------------
# WorkIntentRepository: list_by_workspace_and_status
# ---------------------------------------------------------------------------


async def test_list_by_workspace_and_status_returns_matching(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """list_by_workspace_and_status returns only matching status intents."""
    detected = _make_work_intent(
        workspace_id, what="Detected intent", status=DBIntentStatus.DETECTED
    )
    confirmed = _make_work_intent(
        workspace_id, what="Confirmed intent", status=DBIntentStatus.CONFIRMED
    )
    db_session.add(detected)
    db_session.add(confirmed)
    await db_session.flush()

    results = await intent_repo.list_by_workspace_and_status(workspace_id, IntentStatus.DETECTED)
    assert len(results) == 1
    assert results[0].what == "Detected intent"


async def test_list_by_workspace_and_status_excludes_other_workspace(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """list_by_workspace_and_status does not leak across workspaces."""
    other_ws_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO workspaces (id, name, slug, owner_id) VALUES (:id, :name, :slug, :owner_id)"
        ),
        {
            "id": str(other_ws_id),
            "name": "Other WS",
            "slug": f"other-{other_ws_id.hex[:6]}",
            "owner_id": str(uuid4()),
        },
    )
    await db_session.flush()

    intent = _make_work_intent(other_ws_id, what="Other workspace intent")
    db_session.add(intent)
    await db_session.flush()

    results = await intent_repo.list_by_workspace_and_status(workspace_id, IntentStatus.DETECTED)
    assert len(results) == 0


async def test_list_by_workspace_and_status_excludes_soft_deleted(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """Soft-deleted intents are excluded by default."""
    intent = _make_work_intent(workspace_id, what="Soft deleted intent")
    db_session.add(intent)
    await db_session.flush()

    # Soft delete
    await intent_repo.delete(intent, hard=False)
    await db_session.flush()

    results = await intent_repo.list_by_workspace_and_status(workspace_id, IntentStatus.DETECTED)
    assert len(results) == 0


async def test_list_by_workspace_and_status_includes_deleted_when_requested(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """include_deleted=True returns soft-deleted intents."""
    intent = _make_work_intent(workspace_id, what="Soft deleted intent")
    db_session.add(intent)
    await db_session.flush()

    await intent_repo.delete(intent, hard=False)
    await db_session.flush()

    results = await intent_repo.list_by_workspace_and_status(
        workspace_id, IntentStatus.DETECTED, include_deleted=True
    )
    assert len(results) == 1


# ---------------------------------------------------------------------------
# WorkIntentRepository: list_by_parent_intent
# ---------------------------------------------------------------------------


async def test_list_by_parent_intent_returns_children(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """list_by_parent_intent returns sub-intents for a parent."""
    parent = _make_work_intent(workspace_id, what="Parent intent")
    db_session.add(parent)
    await db_session.flush()

    child1 = _make_work_intent(
        workspace_id, what="Child 1", parent_intent_id=parent.id, confidence=0.8
    )
    child2 = _make_work_intent(
        workspace_id, what="Child 2", parent_intent_id=parent.id, confidence=0.7
    )
    db_session.add(child1)
    db_session.add(child2)
    await db_session.flush()

    results = await intent_repo.list_by_parent_intent(parent.id)
    assert len(results) == 2


async def test_list_by_parent_intent_empty_for_no_children(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """list_by_parent_intent returns empty when no children exist."""
    results = await intent_repo.list_by_parent_intent(uuid4())
    assert list(results) == []


# ---------------------------------------------------------------------------
# WorkIntentRepository: batch_top_by_confidence
# ---------------------------------------------------------------------------


async def test_batch_top_by_confidence_respects_limit(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """batch_top_by_confidence returns at most `limit` results."""
    for i in range(5):
        intent = _make_work_intent(workspace_id, what=f"Intent {i}", confidence=0.9 - i * 0.05)
        db_session.add(intent)
    await db_session.flush()

    results = await intent_repo.batch_top_by_confidence(workspace_id, min_confidence=0.5, limit=3)
    assert len(results) == 3


async def test_batch_top_by_confidence_filters_by_threshold(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """batch_top_by_confidence excludes intents below min_confidence."""
    high = _make_work_intent(workspace_id, what="High confidence", confidence=0.9)
    low = _make_work_intent(workspace_id, what="Low confidence", confidence=0.4)
    db_session.add(high)
    db_session.add(low)
    await db_session.flush()

    results = await intent_repo.batch_top_by_confidence(workspace_id, min_confidence=0.7, limit=10)
    assert len(results) == 1
    assert results[0].what == "High confidence"


# ---------------------------------------------------------------------------
# WorkIntentRepository: get_by_dedup_hash
# ---------------------------------------------------------------------------


async def test_get_by_dedup_hash_returns_match(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """get_by_dedup_hash returns the matching intent."""
    what = "Implement JWT auth"
    dedup_hash = DomainWorkIntent.compute_dedup_hash(what)
    intent = _make_work_intent(workspace_id, what=what, dedup_hash=dedup_hash)
    db_session.add(intent)
    await db_session.flush()

    result = await intent_repo.get_by_dedup_hash(workspace_id, dedup_hash)
    assert result is not None
    assert result.what == what


async def test_get_by_dedup_hash_returns_none_for_unknown(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """get_by_dedup_hash returns None if no match found."""
    result = await intent_repo.get_by_dedup_hash(workspace_id, "a" * 64)
    assert result is None


async def test_get_by_dedup_hash_scoped_to_workspace(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """get_by_dedup_hash does not find intents in other workspaces."""
    other_ws_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO workspaces (id, name, slug, owner_id) VALUES (:id, :name, :slug, :owner_id)"
        ),
        {
            "id": str(other_ws_id),
            "name": "WS2",
            "slug": f"ws2-{other_ws_id.hex[:6]}",
            "owner_id": str(uuid4()),
        },
    )
    await db_session.flush()

    what = "Shared description"
    dedup_hash = DomainWorkIntent.compute_dedup_hash(what)
    intent = _make_work_intent(other_ws_id, what=what, dedup_hash=dedup_hash)
    db_session.add(intent)
    await db_session.flush()

    result = await intent_repo.get_by_dedup_hash(workspace_id, dedup_hash)
    assert result is None


# ---------------------------------------------------------------------------
# WorkIntentRepository: list_by_source_block
# ---------------------------------------------------------------------------


async def test_list_by_source_block_returns_matching(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    workspace_id,
) -> None:
    """list_by_source_block returns intents from the specified block."""
    block_id = uuid4()
    intent1 = _make_work_intent(workspace_id, what="From block 1", source_block_id=block_id)
    intent2 = _make_work_intent(workspace_id, what="Different block", source_block_id=uuid4())
    db_session.add(intent1)
    db_session.add(intent2)
    await db_session.flush()

    results = await intent_repo.list_by_source_block(block_id, workspace_id)
    assert len(results) == 1
    assert results[0].what == "From block 1"


# ---------------------------------------------------------------------------
# IntentArtifactRepository: list_by_intent
# ---------------------------------------------------------------------------


async def test_list_by_intent_returns_artifacts(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    artifact_repo: IntentArtifactRepository,
    workspace_id,
) -> None:
    """list_by_intent returns all artifacts for a given intent."""
    intent = _make_work_intent(workspace_id)
    db_session.add(intent)
    await db_session.flush()

    a1 = IntentArtifact(
        id=uuid4(),
        intent_id=intent.id,
        artifact_type=ArtifactType.ISSUE,
        reference_id=uuid4(),
        reference_type="issue",
    )
    a2 = IntentArtifact(
        id=uuid4(),
        intent_id=intent.id,
        artifact_type=ArtifactType.NOTE,
        reference_id=uuid4(),
        reference_type="note",
    )
    db_session.add(a1)
    db_session.add(a2)
    await db_session.flush()

    results = await artifact_repo.list_by_intent(intent.id)
    assert len(results) == 2


async def test_list_by_intent_empty_for_no_artifacts(
    db_session: AsyncSession,
    artifact_repo: IntentArtifactRepository,
    workspace_id,
) -> None:
    """list_by_intent returns empty when no artifacts exist."""
    results = await artifact_repo.list_by_intent(uuid4())
    assert list(results) == []


async def test_list_by_intent_excludes_soft_deleted(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    artifact_repo: IntentArtifactRepository,
    workspace_id,
) -> None:
    """list_by_intent excludes soft-deleted artifacts by default."""
    intent = _make_work_intent(workspace_id)
    db_session.add(intent)
    await db_session.flush()

    artifact = IntentArtifact(
        id=uuid4(),
        intent_id=intent.id,
        artifact_type=ArtifactType.ISSUE,
        reference_id=uuid4(),
        reference_type="issue",
    )
    db_session.add(artifact)
    await db_session.flush()

    await artifact_repo.delete(artifact, hard=False)
    await db_session.flush()

    results = await artifact_repo.list_by_intent(intent.id)
    assert list(results) == []


# ---------------------------------------------------------------------------
# IntentArtifactRepository: list_by_reference
# ---------------------------------------------------------------------------


async def test_list_by_reference_returns_matching(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    artifact_repo: IntentArtifactRepository,
    workspace_id,
) -> None:
    """list_by_reference returns artifacts pointing to the given reference."""
    intent = _make_work_intent(workspace_id)
    db_session.add(intent)
    await db_session.flush()

    ref_id = uuid4()
    artifact = IntentArtifact(
        id=uuid4(),
        intent_id=intent.id,
        artifact_type=ArtifactType.ISSUE,
        reference_id=ref_id,
        reference_type="issue",
    )
    db_session.add(artifact)
    await db_session.flush()

    results = await artifact_repo.list_by_reference(ref_id)
    assert len(results) == 1


async def test_list_by_reference_filters_by_artifact_type(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    artifact_repo: IntentArtifactRepository,
    workspace_id,
) -> None:
    """list_by_reference with artifact_type filter returns only matching type."""
    intent = _make_work_intent(workspace_id)
    db_session.add(intent)
    await db_session.flush()

    ref_id = uuid4()
    issue_artifact = IntentArtifact(
        id=uuid4(),
        intent_id=intent.id,
        artifact_type=ArtifactType.ISSUE,
        reference_id=ref_id,
        reference_type="issue",
    )
    note_artifact = IntentArtifact(
        id=uuid4(),
        intent_id=intent.id,
        artifact_type=ArtifactType.NOTE,
        reference_id=ref_id,
        reference_type="note",
    )
    db_session.add(issue_artifact)
    db_session.add(note_artifact)
    await db_session.flush()

    results = await artifact_repo.list_by_reference(ref_id, artifact_type=ArtifactType.ISSUE)
    assert len(results) == 1
    assert results[0].artifact_type == ArtifactType.ISSUE


# ---------------------------------------------------------------------------
# IntentArtifactRepository: bulk_create
# ---------------------------------------------------------------------------


async def test_bulk_create_inserts_all(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    artifact_repo: IntentArtifactRepository,
    workspace_id,
) -> None:
    """bulk_create inserts all provided artifacts and returns them with IDs."""
    intent = _make_work_intent(workspace_id)
    db_session.add(intent)
    await db_session.flush()

    artifacts = [
        IntentArtifact(
            id=uuid4(),
            intent_id=intent.id,
            artifact_type=ArtifactType.ISSUE,
            reference_id=uuid4(),
            reference_type="issue",
        )
        for _ in range(3)
    ]

    created = await artifact_repo.bulk_create(artifacts)
    assert len(created) == 3
    assert all(a.id is not None for a in created)
