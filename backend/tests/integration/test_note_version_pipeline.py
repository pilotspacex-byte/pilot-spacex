"""Integration tests for Feature 017 note versioning pipeline.

Tests the full service-layer pipeline:
  - VersionSnapshotService (T-206)
  - VersionDiffService (T-208)
  - VersionRestoreService (T-209, C-9 optimistic lock)
  - VersionDigestService (T-210, cache-first)
  - ImpactAnalysisService (T-211)
  - RetentionService (T-212)
  - VersioningSkillHook (T-213)

Feature 017: Note Versioning — Sprint 1 (T-215 Integration Tests)
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.application.services.version.diff_service import (
    VersionDiffService,
)
from pilot_space.application.services.version.digest_service import VersionDigestService
from pilot_space.application.services.version.impact_service import (
    ImpactAnalysisService,
    ReferenceType,
)
from pilot_space.application.services.version.restore_service import (
    ConcurrentRestoreError,
    RestorePayload,
    VersionRestoreService,
)
from pilot_space.application.services.version.retention_service import (
    RetentionPayload,
    RetentionService,
)
from pilot_space.application.services.version.snapshot_service import (
    SnapshotPayload,
    VersionSnapshotService,
)
from pilot_space.domain.note_version import VersionTrigger
from pilot_space.infrastructure.database.models.note_version import (
    NoteVersion as NoteVersionModel,
    VersionTrigger as ModelTrigger,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOTE_ID = uuid.UUID("11111111-2222-3333-4444-555555555551")
_WS_ID = uuid.UUID("11111111-2222-3333-4444-555555555552")
_USER_ID = uuid.UUID("11111111-2222-3333-4444-555555555553")
_V1_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeee01")
_V2_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeee02")

_CONTENT_V1: dict[str, Any] = {
    "type": "doc",
    "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Hello world PS-1"}]},
    ],
}

_CONTENT_V2: dict[str, Any] = {
    "type": "doc",
    "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Hello world PS-1 updated"}]},
        {"type": "paragraph", "content": [{"type": "text", "text": "New paragraph PS-2"}]},
    ],
}


def _make_db_version(
    *,
    version_id: uuid.UUID = _V1_ID,
    note_id: uuid.UUID = _NOTE_ID,
    workspace_id: uuid.UUID = _WS_ID,
    trigger: ModelTrigger = ModelTrigger.MANUAL,
    content: dict[str, Any] | None = None,
    label: str | None = "v1",
    pinned: bool = False,
    version_number: int = 1,
    digest: str | None = None,
) -> MagicMock:
    """Build a lightweight mock of the NoteVersionModel ORM object."""
    m = MagicMock(spec=NoteVersionModel)
    m.id = version_id
    m.note_id = note_id
    m.workspace_id = workspace_id
    m.trigger = trigger
    m.content = content or _CONTENT_V1
    m.label = label
    m.pinned = pinned
    m.version_number = version_number
    m.digest = digest
    from datetime import UTC, datetime

    m.created_at = datetime.now(tz=UTC)
    return m


def _make_note(content: dict[str, Any] = _CONTENT_V1) -> MagicMock:
    m = MagicMock()
    m.id = _NOTE_ID
    m.workspace_id = _WS_ID
    m.content = content
    return m


# ---------------------------------------------------------------------------
# VersionSnapshotService
# ---------------------------------------------------------------------------


class TestVersionSnapshotServiceIntegration:
    """Tests for VersionSnapshotService.execute()."""

    @pytest.mark.asyncio
    async def test_snapshot_happy_path(self) -> None:
        """Creates a version record from current note content."""
        session = MagicMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        note_repo = MagicMock()
        note_repo.get_by_id = AsyncMock(return_value=_make_note())

        version_repo = MagicMock()
        version_repo.get_max_version_number = AsyncMock(return_value=3)

        # After refresh, set the id on the db_version
        async def _refresh(obj: Any) -> None:
            obj.id = _V1_ID
            obj.version_number = 4
            from datetime import UTC, datetime

            obj.created_at = datetime.now(tz=UTC)

        session.refresh.side_effect = _refresh

        svc = VersionSnapshotService(
            session=session, note_repo=note_repo, version_repo=version_repo
        )
        payload = SnapshotPayload(
            note_id=_NOTE_ID,
            workspace_id=_WS_ID,
            trigger=VersionTrigger.MANUAL,
            created_by=_USER_ID,
        )
        result = await svc.execute(payload)

        assert result.version.version_number == 4
        assert result.version.trigger == VersionTrigger.MANUAL
        assert result.version.content == _CONTENT_V1
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_snapshot_note_not_found_raises(self) -> None:
        """Raises NotFoundError when note doesn't exist."""
        from pilot_space.domain.exceptions import NotFoundError

        session = MagicMock()
        note_repo = MagicMock()
        note_repo.get_by_id = AsyncMock(return_value=None)
        version_repo = MagicMock()
        version_repo.get_max_version_number = AsyncMock(return_value=0)

        svc = VersionSnapshotService(
            session=session, note_repo=note_repo, version_repo=version_repo
        )
        with pytest.raises(NotFoundError, match="not found in workspace"):
            await svc.execute(
                SnapshotPayload(
                    note_id=_NOTE_ID,
                    workspace_id=_WS_ID,
                    trigger=VersionTrigger.AUTO,
                )
            )

    @pytest.mark.asyncio
    async def test_snapshot_wrong_workspace_raises(self) -> None:
        """Raises NotFoundError when note belongs to a different workspace."""
        from pilot_space.domain.exceptions import NotFoundError

        session = MagicMock()
        note = _make_note()
        note.workspace_id = uuid.uuid4()  # Different workspace
        note_repo = MagicMock()
        note_repo.get_by_id = AsyncMock(return_value=note)
        version_repo = MagicMock()
        version_repo.get_max_version_number = AsyncMock(return_value=0)

        svc = VersionSnapshotService(
            session=session, note_repo=note_repo, version_repo=version_repo
        )
        with pytest.raises(NotFoundError, match="not found in workspace"):
            await svc.execute(
                SnapshotPayload(
                    note_id=_NOTE_ID,
                    workspace_id=_WS_ID,
                    trigger=VersionTrigger.AUTO,
                )
            )


# ---------------------------------------------------------------------------
# VersionDiffService
# ---------------------------------------------------------------------------


class TestVersionDiffServiceIntegration:
    """Tests for VersionDiffService.execute()."""

    @pytest.mark.asyncio
    async def test_diff_detects_added_block(self) -> None:
        """Detects that v2 has one more paragraph than v1."""
        v1 = _make_db_version(version_id=_V1_ID, content=_CONTENT_V1)
        v2 = _make_db_version(version_id=_V2_ID, content=_CONTENT_V2)
        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(side_effect=[v1, v2])

        svc = VersionDiffService(session=MagicMock(), version_repo=version_repo)
        result = await svc.execute(_V1_ID, _V2_ID, _NOTE_ID, _WS_ID)

        assert result.has_changes
        assert result.added_count >= 1

    @pytest.mark.asyncio
    async def test_diff_same_content_no_changes(self) -> None:
        """Returns no changes when both versions have identical content."""
        v1 = _make_db_version(version_id=_V1_ID, content=_CONTENT_V1)
        v2 = _make_db_version(version_id=_V2_ID, content=_CONTENT_V1)
        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(side_effect=[v1, v2])

        svc = VersionDiffService(session=MagicMock(), version_repo=version_repo)
        result = await svc.execute(_V1_ID, _V2_ID, _NOTE_ID, _WS_ID)

        assert not result.has_changes
        assert result.modified_count == 0

    @pytest.mark.asyncio
    async def test_diff_version_not_found_raises(self) -> None:
        """Raises NotFoundError when a version is not found."""
        from pilot_space.domain.exceptions import NotFoundError

        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=None)

        svc = VersionDiffService(session=MagicMock(), version_repo=version_repo)
        with pytest.raises(NotFoundError, match="not found"):
            await svc.execute(_V1_ID, _V2_ID, _NOTE_ID, _WS_ID)


# ---------------------------------------------------------------------------
# VersionRestoreService
# ---------------------------------------------------------------------------


class TestVersionRestoreServiceIntegration:
    """Tests for VersionRestoreService.execute() — C-9 optimistic locking."""

    @pytest.mark.asyncio
    async def test_restore_happy_path(self) -> None:
        """Non-destructive restore creates a new version and updates note content."""
        session = MagicMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        async def _refresh(obj: Any) -> None:
            obj.id = _V2_ID
            from datetime import UTC, datetime

            obj.created_at = datetime.now(tz=UTC)

        session.refresh = AsyncMock(side_effect=_refresh)
        session.execute = AsyncMock()

        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=_make_db_version())
        version_repo.get_max_version_number = AsyncMock(return_value=1)

        note = _make_note()
        note_repo = MagicMock()
        note_repo.get_by_id = AsyncMock(return_value=note)

        svc = VersionRestoreService(session=session, note_repo=note_repo, version_repo=version_repo)
        result = await svc.execute(
            RestorePayload(
                version_id=_V1_ID,
                note_id=_NOTE_ID,
                workspace_id=_WS_ID,
                restored_by=_USER_ID,
                expected_version_number=1,
            )
        )

        assert result.new_version.trigger == VersionTrigger.MANUAL
        assert result.restored_from_version_id == _V1_ID
        # Note content must be updated
        assert note.content == _CONTENT_V1

    @pytest.mark.asyncio
    async def test_restore_concurrent_conflict_raises(self) -> None:
        """Raises ConcurrentRestoreError when version_number has advanced (C-9)."""
        session = MagicMock()
        session.execute = AsyncMock()

        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=_make_db_version())
        # Current max = 5, but user expects 1 → conflict
        version_repo.get_max_version_number = AsyncMock(return_value=5)

        note_repo = MagicMock()
        note_repo.get_by_id = AsyncMock(return_value=_make_note())

        svc = VersionRestoreService(session=session, note_repo=note_repo, version_repo=version_repo)
        with pytest.raises(ConcurrentRestoreError) as exc_info:
            await svc.execute(
                RestorePayload(
                    version_id=_V1_ID,
                    note_id=_NOTE_ID,
                    workspace_id=_WS_ID,
                    restored_by=_USER_ID,
                    expected_version_number=1,
                )
            )
        assert exc_info.value.competing_version_number == 5

    @pytest.mark.asyncio
    async def test_restore_version_not_found_raises(self) -> None:
        """Raises NotFoundError when the target version doesn't exist."""
        from pilot_space.domain.exceptions import NotFoundError

        session = MagicMock()
        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=None)
        note_repo = MagicMock()

        svc = VersionRestoreService(session=session, note_repo=note_repo, version_repo=version_repo)
        with pytest.raises(NotFoundError, match="not found for note"):
            await svc.execute(
                RestorePayload(
                    version_id=_V1_ID,
                    note_id=_NOTE_ID,
                    workspace_id=_WS_ID,
                    restored_by=_USER_ID,
                    expected_version_number=1,
                )
            )


# ---------------------------------------------------------------------------
# VersionDigestService
# ---------------------------------------------------------------------------


class TestVersionDigestServiceIntegration:
    """Tests for VersionDigestService.execute() — cache-first, AI fallback."""

    @pytest.mark.asyncio
    async def test_digest_returns_cached(self) -> None:
        """Returns cached digest without calling AI when digest is set."""
        v = _make_db_version(digest="Prior changes summary")
        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=v)

        svc = VersionDigestService(session=MagicMock(), version_repo=version_repo)
        result = await svc.execute(_V1_ID, _NOTE_ID, _WS_ID)

        assert result.from_cache
        assert result.digest == "Prior changes summary"

    @pytest.mark.asyncio
    async def test_digest_fallback_no_api_key(self) -> None:
        """Returns minimal digest without API key."""
        v = _make_db_version(digest=None, content=_CONTENT_V2)
        versions = [
            _make_db_version(version_id=_V2_ID, content=_CONTENT_V2, version_number=2),
            _make_db_version(version_id=_V1_ID, content=_CONTENT_V1, version_number=1),
        ]
        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=v)
        version_repo.list_by_note = AsyncMock(return_value=versions)

        session = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()

        svc = VersionDigestService(
            session=session,
            version_repo=version_repo,
            anthropic_api_key=None,
        )
        v.id = _V2_ID
        result = await svc.execute(_V2_ID, _NOTE_ID, _WS_ID)

        assert not result.from_cache
        assert "block" in result.digest.lower()

    @pytest.mark.asyncio
    async def test_digest_version_not_found_raises(self) -> None:
        """Raises NotFoundError when version not found."""
        from pilot_space.domain.exceptions import NotFoundError

        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=None)

        svc = VersionDigestService(session=MagicMock(), version_repo=version_repo)
        with pytest.raises(NotFoundError, match="not found for note"):
            await svc.execute(_V1_ID, _NOTE_ID, _WS_ID)


# ---------------------------------------------------------------------------
# ImpactAnalysisService
# ---------------------------------------------------------------------------


class TestImpactAnalysisServiceIntegration:
    """Tests for ImpactAnalysisService.execute()."""

    @pytest.mark.asyncio
    async def test_impact_detects_issue_refs(self) -> None:
        """Detects PS-1 and PS-2 issue references in content."""
        v = _make_db_version(content=_CONTENT_V2)  # contains "PS-1 updated" and "PS-2"
        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=v)

        svc = ImpactAnalysisService(session=MagicMock(), version_repo=version_repo)
        result = await svc.execute(_V1_ID, _NOTE_ID, _WS_ID)

        identifiers = [r.identifier for r in result.issue_references]
        assert "PS-1" in identifiers
        assert "PS-2" in identifiers

    @pytest.mark.asyncio
    async def test_impact_detects_uuid_refs(self) -> None:
        """Detects UUID references (note links) in content."""
        uuid_ref = str(uuid.uuid4())
        content: dict[str, Any] = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": f"See note {uuid_ref}"}]}
            ],
        }
        v = _make_db_version(content=content)
        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=v)

        svc = ImpactAnalysisService(session=MagicMock(), version_repo=version_repo)
        result = await svc.execute(_V1_ID, _NOTE_ID, _WS_ID)

        assert any(r.reference_type == ReferenceType.NOTE for r in result.references)
        assert any(r.identifier == uuid_ref.lower() for r in result.references)

    @pytest.mark.asyncio
    async def test_impact_no_refs(self) -> None:
        """Returns empty references when content has no entity refs."""
        content: dict[str, Any] = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Just plain text."}]}
            ],
        }
        v = _make_db_version(content=content)
        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=v)

        svc = ImpactAnalysisService(session=MagicMock(), version_repo=version_repo)
        result = await svc.execute(_V1_ID, _NOTE_ID, _WS_ID)

        assert result.references == []

    @pytest.mark.asyncio
    async def test_impact_version_not_found_raises(self) -> None:
        """Raises NotFoundError when version not found."""
        from pilot_space.domain.exceptions import NotFoundError

        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=None)

        svc = ImpactAnalysisService(session=MagicMock(), version_repo=version_repo)
        with pytest.raises(NotFoundError, match="not found for note"):
            await svc.execute(_V1_ID, _NOTE_ID, _WS_ID)


# ---------------------------------------------------------------------------
# RetentionService
# ---------------------------------------------------------------------------


class TestRetentionServiceIntegration:
    """Tests for RetentionService.execute()."""

    @pytest.mark.asyncio
    async def test_retention_deletes_excess_versions(self) -> None:
        """Deletes candidates returned by find_retention_candidates."""
        candidates = [_make_db_version(version_id=uuid.uuid4()) for _ in range(5)]
        version_repo = MagicMock()
        version_repo.find_retention_candidates = AsyncMock(return_value=candidates)
        version_repo.batch_delete = AsyncMock(return_value=5)
        version_repo.count_by_note = AsyncMock(return_value=45)

        svc = RetentionService(session=MagicMock(), version_repo=version_repo)
        result = await svc.execute(RetentionPayload(note_id=_NOTE_ID, workspace_id=_WS_ID))

        assert result.deleted_count == 5
        assert result.retained_count == 45
        version_repo.batch_delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retention_no_candidates(self) -> None:
        """Returns zero deleted when no candidates found."""
        version_repo = MagicMock()
        version_repo.find_retention_candidates = AsyncMock(return_value=[])
        version_repo.count_by_note = AsyncMock(return_value=10)

        svc = RetentionService(session=MagicMock(), version_repo=version_repo)
        result = await svc.execute(RetentionPayload(note_id=_NOTE_ID, workspace_id=_WS_ID))

        assert result.deleted_count == 0
        assert result.retained_count == 10

    @pytest.mark.asyncio
    async def test_retention_custom_limits(self) -> None:
        """Passes custom max_count and max_age_days to repository."""
        version_repo = MagicMock()
        version_repo.find_retention_candidates = AsyncMock(return_value=[])
        version_repo.count_by_note = AsyncMock(return_value=5)

        svc = RetentionService(session=MagicMock(), version_repo=version_repo)
        await svc.execute(
            RetentionPayload(
                note_id=_NOTE_ID,
                workspace_id=_WS_ID,
                max_count=20,
                max_age_days=30,
            )
        )

        version_repo.find_retention_candidates.assert_awaited_once_with(
            note_id=_NOTE_ID,
            workspace_id=_WS_ID,
            max_count=20,
            max_age_days=30,
        )


# ---------------------------------------------------------------------------
# GAP-02 + GAP-04: ai_before/ai_after pairing + undo-ai fast path
# ---------------------------------------------------------------------------


class TestAiVersionPairing:
    """GAP-02: ai_before_version_id surfaced on ai_after versions.
    GAP-04: undo-ai fast path via get_latest_ai_before.
    """

    @pytest.mark.asyncio
    async def test_get_ai_before_for_after_returns_closest(self) -> None:
        """get_ai_before_for_after finds the most recent ai_before before the given timestamp."""
        from datetime import UTC, datetime, timedelta

        from pilot_space.infrastructure.database.repositories.note_version_repository import (
            NoteVersionRepository,
        )

        ai_before_id = uuid.uuid4()
        ai_after_time = datetime.now(tz=UTC)
        ai_before_time = ai_after_time - timedelta(seconds=30)

        expected = _make_db_version(
            version_id=ai_before_id,
            trigger=ModelTrigger.AI_BEFORE,
        )
        expected.created_at = ai_before_time

        # Mock the session to return the ai_before version
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=expected)
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = NoteVersionRepository(session=mock_session)
        result = await repo.get_ai_before_for_after(_NOTE_ID, _WS_ID, ai_after_time)

        assert result is not None
        assert result.id == ai_before_id

    @pytest.mark.asyncio
    async def test_get_ai_before_for_after_returns_none_when_no_match(self) -> None:
        """Returns None when no ai_before snapshot precedes the given timestamp."""
        from datetime import UTC, datetime

        from pilot_space.infrastructure.database.repositories.note_version_repository import (
            NoteVersionRepository,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = NoteVersionRepository(session=mock_session)
        result = await repo.get_ai_before_for_after(_NOTE_ID, _WS_ID, datetime.now(tz=UTC))
        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_ai_before_returns_most_recent(self) -> None:
        """get_latest_ai_before returns the most recent ai_before for undo-ai."""
        from pilot_space.infrastructure.database.repositories.note_version_repository import (
            NoteVersionRepository,
        )

        ai_before_id = uuid.uuid4()
        expected = _make_db_version(version_id=ai_before_id, trigger=ModelTrigger.AI_BEFORE)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=expected)
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = NoteVersionRepository(session=mock_session)
        result = await repo.get_latest_ai_before(_NOTE_ID, _WS_ID)

        assert result is not None
        assert result.id == ai_before_id

    @pytest.mark.asyncio
    async def test_get_latest_ai_before_returns_none_when_no_ai_edits(self) -> None:
        """Returns None when the note has never been edited by AI."""
        from pilot_space.infrastructure.database.repositories.note_version_repository import (
            NoteVersionRepository,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = NoteVersionRepository(session=mock_session)
        result = await repo.get_latest_ai_before(_NOTE_ID, _WS_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_undo_ai_restore_uses_ai_before_version(self) -> None:
        """undo-ai endpoint calls restore with the ai_before version ID."""
        from pilot_space.application.services.version.restore_service import (
            RestorePayload,
            VersionRestoreService,
        )

        ai_before_id = uuid.uuid4()
        ai_before_orm = _make_db_version(
            version_id=ai_before_id,
            trigger=ModelTrigger.AI_BEFORE,
        )

        version_repo = MagicMock()
        version_repo.get_latest_ai_before = AsyncMock(return_value=ai_before_orm)
        version_repo.get_by_id_for_note = AsyncMock(return_value=ai_before_orm)
        version_repo.get_max_version_number = AsyncMock(return_value=3)

        session = MagicMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        async def _refresh(obj: Any) -> None:
            obj.id = uuid.uuid4()
            from datetime import UTC, datetime

            obj.created_at = datetime.now(tz=UTC)

        session.refresh = AsyncMock(side_effect=_refresh)
        session.execute = AsyncMock()

        note = _make_note()
        note_repo = MagicMock()
        note_repo.get_by_id = AsyncMock(return_value=note)

        svc = VersionRestoreService(session=session, note_repo=note_repo, version_repo=version_repo)

        # Fetch latest ai_before (as the endpoint does)
        ai_before = await version_repo.get_latest_ai_before(_NOTE_ID, _WS_ID)
        assert ai_before is not None

        result = await svc.execute(
            RestorePayload(
                version_id=ai_before.id,
                note_id=_NOTE_ID,
                workspace_id=_WS_ID,
                restored_by=_USER_ID,
                expected_version_number=3,
            )
        )

        # The restore must target the ai_before version
        assert result.restored_from_version_id == ai_before_id

    @pytest.mark.asyncio
    async def test_undo_ai_conflict_raises_409_equivalent(self) -> None:
        """ConcurrentRestoreError is raised when version_number mismatches during undo-ai."""
        from pilot_space.application.services.version.restore_service import (
            ConcurrentRestoreError,
            RestorePayload,
            VersionRestoreService,
        )

        ai_before_orm = _make_db_version(trigger=ModelTrigger.AI_BEFORE)
        version_repo = MagicMock()
        version_repo.get_by_id_for_note = AsyncMock(return_value=ai_before_orm)
        # Current max = 7, user expects 3 → conflict
        version_repo.get_max_version_number = AsyncMock(return_value=7)

        note_repo = MagicMock()
        note_repo.get_by_id = AsyncMock(return_value=_make_note())

        session = MagicMock()
        session.execute = AsyncMock()

        svc = VersionRestoreService(session=session, note_repo=note_repo, version_repo=version_repo)
        with pytest.raises(ConcurrentRestoreError) as exc_info:
            await svc.execute(
                RestorePayload(
                    version_id=_V1_ID,
                    note_id=_NOTE_ID,
                    workspace_id=_WS_ID,
                    restored_by=_USER_ID,
                    expected_version_number=3,
                )
            )
        assert exc_info.value.competing_version_number == 7
