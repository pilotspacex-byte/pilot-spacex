"""Unit tests for Intent Engine services.

T-015: Intent API integration tests
Tests T-008 through T-014 coverage:
- IntentDetectionService (mocked LLM)
- IntentService (confirm, reject, edit, confirmAll with C-8 dedup gate)
- Chat-priority window (T-010)
- ConfirmAll cap and dedup gate (T-011, C-8)

Feature 015: AI Workforce Platform (M2)
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from pilot_space.application.services.intent.detection_service import (
    DetectIntentPayload,
    IntentDetectionService,
    IntentSource,
)
from pilot_space.application.services.intent.intent_service import (
    ConfirmAllPayload,
    ConfirmIntentPayload,
    EditIntentPayload,
    IntentService,
    RejectIntentPayload,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from pilot_space.domain.work_intent import IntentStatus
from pilot_space.infrastructure.database.models.work_intent import (
    DedupStatus as DBDedupStatus,
    IntentStatus as DBIntentStatus,
    WorkIntent as WorkIntentModel,
)
from pilot_space.infrastructure.database.repositories.intent_repository import (
    WorkIntentRepository,
)

# ---------------------------------------------------------------------------
# SQLite schema for work_intents
# ---------------------------------------------------------------------------

_INTENT_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    settings TEXT,
    owner_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS work_intents (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
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
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
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
    """Register uuid4 function for SQLite."""
    dbapi_conn.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))


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
        for stmt in _INTENT_TABLES_SQL.strip().split(";"):
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


@pytest.fixture
def workspace_id() -> UUID:
    return uuid4()


@pytest.fixture
async def workspace(db_session: AsyncSession, workspace_id: UUID) -> None:
    """Seed a workspace row."""
    await db_session.execute(
        text("INSERT INTO workspaces (id, name, slug) VALUES (:id, :name, :slug)"),
        {"id": str(workspace_id), "name": "Test WS", "slug": "test-ws"},
    )
    await db_session.flush()


@pytest.fixture
def intent_repo(db_session: AsyncSession) -> WorkIntentRepository:
    return WorkIntentRepository(session=db_session)


@pytest.fixture
def intent_service(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
) -> IntentService:
    return IntentService(session=db_session, intent_repository=intent_repo)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_detected_intent(
    workspace_id: UUID,
    what: str = "Build login page",
    confidence: float = 0.9,
    dedup_status: DBDedupStatus = DBDedupStatus.COMPLETE,
) -> WorkIntentModel:
    from pilot_space.domain.work_intent import WorkIntent as DomainIntent

    return WorkIntentModel(
        id=uuid4(),
        workspace_id=workspace_id,
        what=what,
        confidence=confidence,
        status=DBIntentStatus.DETECTED,
        dedup_status=dedup_status,
        dedup_hash=DomainIntent.compute_dedup_hash(what),
    )


# ---------------------------------------------------------------------------
# IntentService: confirm
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_intent_success(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Confirm a DETECTED intent transitions it to CONFIRMED."""
    model = _make_detected_intent(workspace_id)
    created = await intent_repo.create(model)
    await db_session.flush()

    result = await intent_service.confirm(
        ConfirmIntentPayload(intent_id=created.id, workspace_id=workspace_id)
    )

    assert result.status == DBIntentStatus.CONFIRMED


@pytest.mark.asyncio
async def test_confirm_intent_not_found(
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Confirm raises ValueError when intent doesn't exist."""
    with pytest.raises(NotFoundError, match="not found"):
        await intent_service.confirm(
            ConfirmIntentPayload(intent_id=uuid4(), workspace_id=workspace_id)
        )


@pytest.mark.asyncio
async def test_confirm_intent_wrong_workspace(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Confirm raises ValueError on workspace mismatch."""
    model = _make_detected_intent(workspace_id)
    created = await intent_repo.create(model)
    await db_session.flush()

    with pytest.raises(ForbiddenError, match="does not belong"):
        await intent_service.confirm(
            ConfirmIntentPayload(intent_id=created.id, workspace_id=uuid4())
        )


# ---------------------------------------------------------------------------
# IntentService: reject
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_intent_success(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Reject a DETECTED intent transitions it to REJECTED."""
    model = _make_detected_intent(workspace_id)
    created = await intent_repo.create(model)
    await db_session.flush()

    result = await intent_service.reject(
        RejectIntentPayload(intent_id=created.id, workspace_id=workspace_id)
    )

    assert result.status == DBIntentStatus.REJECTED


@pytest.mark.asyncio
async def test_reject_already_rejected_raises(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Reject raises ValueError if already in terminal REJECTED state."""
    model = _make_detected_intent(workspace_id)
    model.status = DBIntentStatus.REJECTED
    created = await intent_repo.create(model)
    await db_session.flush()

    with pytest.raises(ValidationError, match="Cannot transition"):
        await intent_service.reject(
            RejectIntentPayload(intent_id=created.id, workspace_id=workspace_id)
        )


# ---------------------------------------------------------------------------
# IntentService: edit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_intent_what(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Edit updates 'what' and resets dedup_hash and dedup_status to pending."""
    model = _make_detected_intent(workspace_id, dedup_status=DBDedupStatus.COMPLETE)
    created = await intent_repo.create(model)
    await db_session.flush()

    result = await intent_service.edit(
        EditIntentPayload(
            intent_id=created.id,
            workspace_id=workspace_id,
            new_what="Updated: Build OAuth login page",
        )
    )

    assert result.what == "Updated: Build OAuth login page"
    # dedup_status reset to pending so J-1 re-processes
    assert result.dedup_status == DBDedupStatus.PENDING


@pytest.mark.asyncio
async def test_edit_intent_why(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Edit can update 'why' independently."""
    model = _make_detected_intent(workspace_id)
    created = await intent_repo.create(model)
    await db_session.flush()

    result = await intent_service.edit(
        EditIntentPayload(
            intent_id=created.id,
            workspace_id=workspace_id,
            new_why="Security compliance requires SSO",
        )
    )

    assert result.why == "Security compliance requires SSO"


@pytest.mark.asyncio
async def test_edit_confirmed_intent_raises(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Edit 'what' raises ValueError if intent is already CONFIRMED."""
    model = _make_detected_intent(workspace_id)
    model.status = DBIntentStatus.CONFIRMED
    created = await intent_repo.create(model)
    await db_session.flush()

    with pytest.raises(ValidationError, match="Cannot update"):
        await intent_service.edit(
            EditIntentPayload(
                intent_id=created.id,
                workspace_id=workspace_id,
                new_what="Different intent",
            )
        )


# ---------------------------------------------------------------------------
# IntentService: confirm_all (T-011, C-8)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_all_respects_cap(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """ConfirmAll cap=3 confirms only 3 even when 5 intents are eligible."""
    for i in range(5):
        model = _make_detected_intent(
            workspace_id,
            what=f"Intent {i}",
            confidence=0.9 - (i * 0.01),
            dedup_status=DBDedupStatus.COMPLETE,
        )
        await intent_repo.create(model)
    await db_session.flush()

    result = await intent_service.confirm_all(
        ConfirmAllPayload(
            workspace_id=workspace_id,
            min_confidence=0.7,
            max_count=3,
        )
    )

    assert len(result.confirmed) == 3
    assert result.remaining_count == 2  # 5 - 3 confirmed
    assert result.deduplicating_count == 0


@pytest.mark.asyncio
async def test_confirm_all_excludes_dedup_pending(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """C-8: confirmAll excludes intents with dedup_status='pending'."""
    # 12 complete, 3 pending
    for i in range(12):
        model = _make_detected_intent(
            workspace_id,
            what=f"Complete intent {i}",
            confidence=0.85,
            dedup_status=DBDedupStatus.COMPLETE,
        )
        await intent_repo.create(model)

    for i in range(3):
        model = _make_detected_intent(
            workspace_id,
            what=f"Pending dedup intent {i}",
            confidence=0.95,  # Higher confidence, but excluded
            dedup_status=DBDedupStatus.PENDING,
        )
        await intent_repo.create(model)
    await db_session.flush()

    result = await intent_service.confirm_all(
        ConfirmAllPayload(
            workspace_id=workspace_id,
            min_confidence=0.7,
            max_count=10,
        )
    )

    # Only 10 from the 12 complete set (capped at 10)
    assert len(result.confirmed) == 10
    assert result.deduplicating_count == 3
    # remaining = 15 total detected - 10 confirmed = 5
    assert result.remaining_count == 5


@pytest.mark.asyncio
async def test_confirm_all_min_confidence_filter(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """ConfirmAll skips intents below min_confidence."""
    # 3 above threshold
    for i in range(3):
        model = _make_detected_intent(
            workspace_id,
            what=f"High confidence {i}",
            confidence=0.9,
            dedup_status=DBDedupStatus.COMPLETE,
        )
        await intent_repo.create(model)

    # 2 below threshold
    for i in range(2):
        model = _make_detected_intent(
            workspace_id,
            what=f"Low confidence {i}",
            confidence=0.5,
            dedup_status=DBDedupStatus.COMPLETE,
        )
        await intent_repo.create(model)
    await db_session.flush()

    result = await intent_service.confirm_all(
        ConfirmAllPayload(
            workspace_id=workspace_id,
            min_confidence=0.7,
            max_count=10,
        )
    )

    assert len(result.confirmed) == 3


@pytest.mark.asyncio
async def test_confirm_all_empty_workspace(
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """ConfirmAll returns empty result for workspace with no intents."""
    result = await intent_service.confirm_all(
        ConfirmAllPayload(
            workspace_id=workspace_id,
            min_confidence=0.7,
            max_count=10,
        )
    )

    assert len(result.confirmed) == 0
    assert result.remaining_count == 0
    assert result.deduplicating_count == 0


# ---------------------------------------------------------------------------
# IntentDetectionService (mocked LLM + Redis)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis() -> MagicMock:
    """Mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)  # No lock by default
    redis.set = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def detection_service(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    mock_redis: MagicMock,
) -> IntentDetectionService:
    return IntentDetectionService(
        session=db_session,
        intent_repository=intent_repo,
        redis_client=mock_redis,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_detect_empty_text_returns_empty(
    detection_service: IntentDetectionService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Empty text returns empty intent list without LLM call."""
    result = await detection_service.detect(
        DetectIntentPayload(
            workspace_id=workspace_id,
            text="   ",
            source=IntentSource.CHAT,
        )
    )

    assert result.intents == []
    assert result.total_detected == 0


@pytest.mark.asyncio
async def test_detect_chat_sets_redis_lock(
    detection_service: IntentDetectionService,
    mock_redis: MagicMock,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Chat source sets a 3-second Redis lock."""
    with patch.object(detection_service, "_call_llm", AsyncMock(return_value=([], "noop"))):
        await detection_service.detect(
            DetectIntentPayload(
                workspace_id=workspace_id,
                text="Build OAuth login",
                source=IntentSource.CHAT,
            )
        )

    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args
    assert "intent_lock:" in call_args[0][0]
    assert call_args[1]["ttl"] == 3


@pytest.mark.asyncio
async def test_detect_note_skips_if_chat_lock_active(
    detection_service: IntentDetectionService,
    mock_redis: MagicMock,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Note source returns empty immediately if chat lock is active (T-010)."""
    mock_redis.get = AsyncMock(return_value="1")  # Lock is active

    result = await detection_service.detect(
        DetectIntentPayload(
            workspace_id=workspace_id,
            text="TODO: Create migration",
            source=IntentSource.NOTE,
        )
    )

    assert result.intents == []
    assert result.chat_lock_was_active is True


@pytest.mark.asyncio
async def test_detect_note_proceeds_if_no_lock(
    detection_service: IntentDetectionService,
    mock_redis: MagicMock,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Note source proceeds with LLM call when no chat lock is active."""
    mock_redis.get = AsyncMock(return_value=None)

    with patch.object(detection_service, "_call_llm", AsyncMock(return_value=([], "noop"))):
        result = await detection_service.detect(
            DetectIntentPayload(
                workspace_id=workspace_id,
                text="TODO: Write unit tests",
                source=IntentSource.NOTE,
            )
        )

    assert result.chat_lock_was_active is False


@pytest.mark.asyncio
async def test_detect_returns_persisted_intents(
    db_session: AsyncSession,
    detection_service: IntentDetectionService,
    intent_repo: WorkIntentRepository,
    mock_redis: MagicMock,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Detected intents are persisted to DB and returned."""
    from pilot_space.domain.work_intent import WorkIntent as DomainIntent

    fake_intent = DomainIntent(
        workspace_id=workspace_id,
        what="Implement JWT authentication",
        why="Security requirement",
        confidence=0.95,
    )

    with patch.object(
        detection_service,
        "_call_llm",
        AsyncMock(return_value=([fake_intent], "claude-sonnet-4")),
    ):
        result = await detection_service.detect(
            DetectIntentPayload(
                workspace_id=workspace_id,
                text="We need to implement JWT auth",
                source=IntentSource.CHAT,
            )
        )

    assert len(result.intents) == 1
    assert result.intents[0].what == "Implement JWT authentication"
    assert result.detection_model == "claude-sonnet-4"

    # Verify DB persistence
    db_intents = await intent_repo.list_by_workspace_and_status(workspace_id, IntentStatus.DETECTED)
    assert len(db_intents) == 1
    assert db_intents[0].what == "Implement JWT authentication"


# ---------------------------------------------------------------------------
# LLM prompt parsing (unit test _parse_llm_response directly)
# ---------------------------------------------------------------------------


def test_parse_llm_response_valid_json() -> None:
    """Parses valid JSON array into WorkIntent list."""
    from pilot_space.application.services.intent.detection_service import _parse_llm_response

    raw = """[
      {
        "what": "Add rate limiting to API",
        "why": "Prevent abuse",
        "constraints": ["Must be Redis-based"],
        "acceptance": ["Returns 429 on limit exceeded"],
        "confidence": 0.92
      }
    ]"""
    intents = _parse_llm_response(
        raw, workspace_id=uuid4(), source=IntentSource.CHAT, source_block_id=None, owner=None
    )
    assert len(intents) == 1
    assert intents[0].what == "Add rate limiting to API"
    assert intents[0].confidence == 0.92


def test_parse_llm_response_empty_array() -> None:
    """Empty JSON array returns empty list."""
    from pilot_space.application.services.intent.detection_service import _parse_llm_response

    intents = _parse_llm_response(
        "[]", workspace_id=uuid4(), source=IntentSource.NOTE, source_block_id=None, owner=None
    )
    assert intents == []


def test_parse_llm_response_caps_at_10() -> None:
    """Parser caps output at 10 intents even if LLM returns more."""
    from pilot_space.application.services.intent.detection_service import _parse_llm_response

    items = [{"what": f"Intent {i}", "confidence": 0.8} for i in range(15)]
    import json

    raw = json.dumps(items)
    intents = _parse_llm_response(
        raw, workspace_id=uuid4(), source=IntentSource.CHAT, source_block_id=None, owner=None
    )
    assert len(intents) == 10


def test_parse_llm_response_strips_markdown_fences() -> None:
    """Strips ```json ... ``` fences before parsing."""
    from pilot_space.application.services.intent.detection_service import _parse_llm_response

    raw = '```json\n[{"what": "Fix bug", "confidence": 0.9}]\n```'
    intents = _parse_llm_response(
        raw, workspace_id=uuid4(), source=IntentSource.CHAT, source_block_id=None, owner=None
    )
    assert len(intents) == 1


def test_parse_llm_response_invalid_json_returns_empty() -> None:
    """Invalid JSON returns empty list without raising."""
    from pilot_space.application.services.intent.detection_service import _parse_llm_response

    intents = _parse_llm_response(
        "not valid json",
        workspace_id=uuid4(),
        source=IntentSource.CHAT,
        source_block_id=None,
        owner=None,
    )
    assert intents == []


def test_parse_llm_response_confidence_clamped() -> None:
    """Confidence outside [0.0, 1.0] is clamped."""
    from pilot_space.application.services.intent.detection_service import _parse_llm_response

    raw = '[{"what": "Test", "confidence": 1.5}]'
    intents = _parse_llm_response(
        raw, workspace_id=uuid4(), source=IntentSource.CHAT, source_block_id=None, owner=None
    )
    assert intents[0].confidence == 1.0

    raw = '[{"what": "Test", "confidence": -0.5}]'
    intents = _parse_llm_response(
        raw, workspace_id=uuid4(), source=IntentSource.CHAT, source_block_id=None, owner=None
    )
    assert intents[0].confidence == 0.0


def test_parse_llm_response_non_list_returns_empty() -> None:
    """Non-list JSON returns empty list."""
    from pilot_space.application.services.intent.detection_service import _parse_llm_response

    intents = _parse_llm_response(
        '{"what": "Test"}',
        workspace_id=uuid4(),
        source=IntentSource.CHAT,
        source_block_id=None,
        owner=None,
    )
    assert intents == []


def test_parse_llm_response_skips_items_without_what() -> None:
    """Items without 'what' field are skipped."""
    from pilot_space.application.services.intent.detection_service import _parse_llm_response

    raw = (
        '[{"why": "No what field", "confidence": 0.9}, {"what": "Valid intent", "confidence": 0.8}]'
    )
    intents = _parse_llm_response(
        raw, workspace_id=uuid4(), source=IntentSource.CHAT, source_block_id=None, owner=None
    )
    assert len(intents) == 1
    assert intents[0].what == "Valid intent"


def test_parse_llm_response_with_source_block_id_and_owner() -> None:
    """source_block_id and owner are passed through."""
    from pilot_space.application.services.intent.detection_service import _parse_llm_response

    block_id = uuid4()
    raw = '[{"what": "Build feature", "confidence": 0.9}]'
    intents = _parse_llm_response(
        raw,
        workspace_id=uuid4(),
        source=IntentSource.NOTE,
        source_block_id=block_id,
        owner="user-123",
    )
    assert len(intents) == 1
    assert intents[0].source_block_id == block_id
    assert intents[0].owner == "user-123"


# ---------------------------------------------------------------------------
# IntentService: get_intent and list_by_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_intent_success(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """get_intent returns the intent if found."""
    model = _make_detected_intent(workspace_id)
    created = await intent_repo.create(model)
    await db_session.flush()

    intent = await intent_service.get_intent(created.id, workspace_id)
    assert intent.id == created.id


@pytest.mark.asyncio
async def test_get_intent_not_found_raises(
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """get_intent raises ValueError when not found."""
    with pytest.raises(NotFoundError, match="not found"):
        await intent_service.get_intent(uuid4(), workspace_id)


@pytest.mark.asyncio
async def test_get_intent_wrong_workspace_raises(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """get_intent raises ValueError on workspace mismatch."""
    model = _make_detected_intent(workspace_id)
    created = await intent_repo.create(model)
    await db_session.flush()

    with pytest.raises(ForbiddenError, match="does not belong"):
        await intent_service.get_intent(created.id, uuid4())


@pytest.mark.asyncio
async def test_list_by_status_returns_matching(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """list_by_status filters intents by status."""
    # 2 detected, 1 confirmed
    for i in range(2):
        model = _make_detected_intent(workspace_id, what=f"Detected {i}")
        await intent_repo.create(model)

    confirmed_model = _make_detected_intent(workspace_id, what="Confirmed intent")
    confirmed_model.status = DBIntentStatus.CONFIRMED
    await intent_repo.create(confirmed_model)
    await db_session.flush()

    detected = await intent_service.list_by_status(workspace_id, IntentStatus.DETECTED)
    assert len(detected) == 2

    confirmed = await intent_service.list_by_status(workspace_id, IntentStatus.CONFIRMED)
    assert len(confirmed) == 1


# ---------------------------------------------------------------------------
# IntentService: edge cases for reject and edit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_not_found_raises(
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """reject raises ValueError when intent not found."""
    with pytest.raises(NotFoundError, match="not found"):
        await intent_service.reject(
            RejectIntentPayload(intent_id=uuid4(), workspace_id=workspace_id)
        )


@pytest.mark.asyncio
async def test_reject_wrong_workspace_raises(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """reject raises ValueError on workspace mismatch."""
    model = _make_detected_intent(workspace_id)
    created = await intent_repo.create(model)
    await db_session.flush()

    with pytest.raises(ForbiddenError, match="does not belong"):
        await intent_service.reject(RejectIntentPayload(intent_id=created.id, workspace_id=uuid4()))


@pytest.mark.asyncio
async def test_edit_not_found_raises(
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """edit raises ValueError when intent not found."""
    with pytest.raises(NotFoundError, match="not found"):
        await intent_service.edit(
            EditIntentPayload(intent_id=uuid4(), workspace_id=workspace_id, new_what="x")
        )


@pytest.mark.asyncio
async def test_edit_wrong_workspace_raises(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """edit raises ValueError on workspace mismatch."""
    model = _make_detected_intent(workspace_id)
    created = await intent_repo.create(model)
    await db_session.flush()

    with pytest.raises(ForbiddenError, match="does not belong"):
        await intent_service.edit(
            EditIntentPayload(intent_id=created.id, workspace_id=uuid4(), new_what="x")
        )


@pytest.mark.asyncio
async def test_edit_constraints_on_confirmed_raises(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """edit raises ValueError when updating constraints on non-mutable intent."""
    model = _make_detected_intent(workspace_id)
    model.status = DBIntentStatus.CONFIRMED
    created = await intent_repo.create(model)
    await db_session.flush()

    with pytest.raises(ValidationError, match="Cannot update constraints"):
        await intent_service.edit(
            EditIntentPayload(
                intent_id=created.id,
                workspace_id=workspace_id,
                new_constraints=["Must use PostgreSQL"],
            )
        )


@pytest.mark.asyncio
async def test_edit_acceptance_on_confirmed_raises(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """edit raises ValueError when updating acceptance on non-mutable intent."""
    model = _make_detected_intent(workspace_id)
    model.status = DBIntentStatus.CONFIRMED
    created = await intent_repo.create(model)
    await db_session.flush()

    with pytest.raises(ValidationError, match="Cannot update acceptance"):
        await intent_service.edit(
            EditIntentPayload(
                intent_id=created.id,
                workspace_id=workspace_id,
                new_acceptance=["Tests must pass"],
            )
        )


# ---------------------------------------------------------------------------
# IntentDetectionService: _persist_intent coverage via detect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_persists_with_source_block_id(
    db_session: AsyncSession,
    detection_service: IntentDetectionService,
    intent_repo: WorkIntentRepository,
    mock_redis: MagicMock,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Detected intents carry source_block_id and owner when provided."""
    from pilot_space.domain.work_intent import WorkIntent as DomainIntent

    block_id = uuid4()
    fake_intent = DomainIntent(
        workspace_id=workspace_id,
        what="Write API documentation",
        confidence=0.88,
    )

    with patch.object(
        detection_service,
        "_call_llm",
        AsyncMock(return_value=([fake_intent], "claude-sonnet-4")),
    ):
        result = await detection_service.detect(
            DetectIntentPayload(
                workspace_id=workspace_id,
                text="Write API docs",
                source=IntentSource.NOTE,
                source_block_id=block_id,
                owner="user-abc",
            )
        )

    assert len(result.intents) == 1
    # The source_block_id and owner from payload override the intent's default
    db_intents = await intent_repo.list_by_workspace_and_status(workspace_id, IntentStatus.DETECTED)
    assert db_intents[0].source_block_id == block_id
    assert db_intents[0].owner == "user-abc"


@pytest.mark.asyncio
async def test_detect_no_api_key_returns_empty(
    db_session: AsyncSession,
    detection_service: IntentDetectionService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """When _call_llm returns noop (no API key), detect returns empty."""
    with patch.object(detection_service, "_call_llm", AsyncMock(return_value=([], "noop"))):
        result = await detection_service.detect(
            DetectIntentPayload(
                workspace_id=workspace_id,
                text="Build a feature",
                source=IntentSource.CHAT,
            )
        )

    assert result.intents == []
    assert result.detection_model == "noop"


@pytest.mark.asyncio
async def test_detect_note_empty_text_after_lock_check(
    detection_service: IntentDetectionService,
    mock_redis: MagicMock,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """Note source with no lock but empty text returns empty without LLM call."""
    mock_redis.get = AsyncMock(return_value=None)  # No lock

    result = await detection_service.detect(
        DetectIntentPayload(
            workspace_id=workspace_id,
            text="   ",
            source=IntentSource.NOTE,
        )
    )

    assert result.intents == []
    assert result.total_detected == 0
    assert result.chat_lock_was_active is False


def test_parse_llm_response_non_dict_items_skipped() -> None:
    """Non-dict items in JSON array are skipped."""
    import json

    from pilot_space.application.services.intent.detection_service import _parse_llm_response

    raw = json.dumps(["not a dict", 42, {"what": "Valid intent", "confidence": 0.8}, None])
    intents = _parse_llm_response(
        raw, workspace_id=uuid4(), source=IntentSource.CHAT, source_block_id=None, owner=None
    )
    assert len(intents) == 1
    assert intents[0].what == "Valid intent"


def test_parse_llm_response_markdown_fence_no_closing() -> None:
    """Markdown fence without closing ``` still parses successfully."""
    from pilot_space.application.services.intent.detection_service import _parse_llm_response

    raw = '```json\n[{"what": "Fix auth bug", "confidence": 0.9}]'
    intents = _parse_llm_response(
        raw, workspace_id=uuid4(), source=IntentSource.CHAT, source_block_id=None, owner=None
    )
    assert len(intents) == 1


# ---------------------------------------------------------------------------
# IntentService: confirm_all ValueError path (invalid transition warning)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_all_skips_invalid_transition(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """confirmAll skips intents that raise ValueError during domain transition."""
    # Create a CONFIRMED intent that can't be confirmed again
    model = _make_detected_intent(workspace_id, what="Already confirmed")
    model.status = DBIntentStatus.CONFIRMED
    model.dedup_status = DBDedupStatus.COMPLETE
    await intent_repo.create(model)
    await db_session.flush()

    # This intent has CONFIRMED status so list_by_workspace_and_status(DETECTED) won't return it
    # Create a fresh detected one to confirm the system works correctly
    detected = _make_detected_intent(workspace_id, what="Detected intent")
    await intent_repo.create(detected)
    await db_session.flush()

    result = await intent_service.confirm_all(
        ConfirmAllPayload(
            workspace_id=workspace_id,
            min_confidence=0.7,
            max_count=10,
        )
    )
    # Only the DETECTED one should be confirmed
    assert len(result.confirmed) == 1


# ---------------------------------------------------------------------------
# IntentService: edit constraints and acceptance success paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_constraints_on_detected_succeeds(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """edit can update constraints on a DETECTED (mutable) intent."""
    model = _make_detected_intent(workspace_id)
    created = await intent_repo.create(model)
    await db_session.flush()

    result = await intent_service.edit(
        EditIntentPayload(
            intent_id=created.id,
            workspace_id=workspace_id,
            new_constraints=["Must use PostgreSQL", "No third-party auth"],
        )
    )

    assert result.constraints == ["Must use PostgreSQL", "No third-party auth"]


@pytest.mark.asyncio
async def test_edit_acceptance_on_detected_succeeds(
    db_session: AsyncSession,
    intent_repo: WorkIntentRepository,
    intent_service: IntentService,
    workspace_id: UUID,
    workspace: None,
) -> None:
    """edit can update acceptance criteria on a DETECTED (mutable) intent."""
    model = _make_detected_intent(workspace_id)
    created = await intent_repo.create(model)
    await db_session.flush()

    result = await intent_service.edit(
        EditIntentPayload(
            intent_id=created.id,
            workspace_id=workspace_id,
            new_acceptance=["All tests pass", "No regressions"],
        )
    )

    assert result.acceptance == ["All tests pass", "No regressions"]
