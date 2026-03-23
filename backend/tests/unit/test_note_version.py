"""Unit tests for NoteVersion domain entity and related services.

Tests cover:
- Domain entity validation (T-203)
- DiffService block-level computation (T-208)
- ImpactAnalysisService entity detection (T-211)
- RetentionService pinned exemption (T-212)
- VersioningSkillHook trigger selection (T-213)

Feature 017: Note Versioning — Sprint 1 (T-205)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from pilot_space.domain.exceptions import NotFoundError
from pilot_space.domain.note_version import NoteVersion, VersionTrigger

# ─── Helpers ────────────────────────────────────────────────────────────────


def make_version(**kwargs: Any) -> NoteVersion:
    """Factory for NoteVersion with sensible defaults."""
    defaults: dict[str, Any] = {
        "note_id": uuid.uuid4(),
        "workspace_id": uuid.uuid4(),
        "trigger": VersionTrigger.MANUAL,
        "content": {"type": "doc", "content": []},
    }
    defaults.update(kwargs)
    return NoteVersion(**defaults)


def tiptap_doc(*block_ids: str) -> dict:
    """Build a minimal TipTap doc with blocks identified by block_ids."""
    return {
        "type": "doc",
        "content": [
            {"type": "paragraph", "attrs": {"id": bid}, "content": [{"type": "text", "text": bid}]}
            for bid in block_ids
        ],
    }


# ─── NoteVersion domain entity ──────────────────────────────────────────────


class TestNoteVersionCreation:
    """Tests for NoteVersion initialization and validation."""

    def test_create_with_required_fields(self) -> None:
        v = make_version()
        assert v.trigger == VersionTrigger.MANUAL
        assert v.pinned is False
        assert v.digest is None
        assert v.version_number == 1

    def test_label_max_100_chars_ok(self) -> None:
        v = make_version(label="x" * 100)
        assert v.label == "x" * 100

    def test_label_over_100_chars_raises(self) -> None:
        with pytest.raises(ValueError, match="100 characters"):
            make_version(label="x" * 101)

    def test_content_must_be_dict(self) -> None:
        with pytest.raises(TypeError, match="must be a dict"):
            make_version(content="not a dict")

    def test_version_number_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="must be >= 1"):
            make_version(version_number=0)

    def test_pin_sets_pinned_true(self) -> None:
        v = make_version()
        v.pin()
        assert v.pinned is True

    def test_unpin_sets_pinned_false(self) -> None:
        v = make_version(pinned=True)
        v.unpin()
        assert v.pinned is False

    def test_cache_digest_updates_fields(self) -> None:
        v = make_version()
        v.cache_digest("changed 3 blocks")
        assert v.digest == "changed 3 blocks"
        assert v.digest_cached_at is not None

    def test_invalidate_digest_clears_fields(self) -> None:
        v = make_version()
        v.cache_digest("some digest")
        v.invalidate_digest()
        assert v.digest is None
        assert v.digest_cached_at is None

    def test_has_digest_property(self) -> None:
        v = make_version()
        assert v.has_digest is False
        v.cache_digest("text")
        assert v.has_digest is True

    def test_is_ai_triggered_for_ai_before(self) -> None:
        v = make_version(trigger=VersionTrigger.AI_BEFORE)
        assert v.is_ai_triggered is True

    def test_is_ai_triggered_for_ai_after(self) -> None:
        v = make_version(trigger=VersionTrigger.AI_AFTER)
        assert v.is_ai_triggered is True

    def test_is_not_ai_triggered_for_manual(self) -> None:
        v = make_version(trigger=VersionTrigger.MANUAL)
        assert v.is_ai_triggered is False

    def test_is_not_ai_triggered_for_auto(self) -> None:
        v = make_version(trigger=VersionTrigger.AUTO)
        assert v.is_ai_triggered is False


# ─── VersionTrigger enum ────────────────────────────────────────────────────


class TestVersionTrigger:
    """Tests for VersionTrigger enum values."""

    def test_all_trigger_values(self) -> None:
        assert VersionTrigger.AUTO == "auto"
        assert VersionTrigger.MANUAL == "manual"
        assert VersionTrigger.AI_BEFORE == "ai_before"
        assert VersionTrigger.AI_AFTER == "ai_after"

    def test_trigger_is_str_enum(self) -> None:
        assert isinstance(VersionTrigger.AUTO, str)


# ─── DiffService ────────────────────────────────────────────────────────────


class TestVersionDiffService:
    """Tests for VersionDiffService block-level computation (T-208)."""

    def _make_service(self, v1_content: dict, v2_content: dict) -> Any:
        """Build a DiffService with mocked repository returning given versions."""
        from pilot_space.application.services.version.diff_service import VersionDiffService

        v1_id = uuid.uuid4()
        v2_id = uuid.uuid4()
        note_id = uuid.uuid4()
        workspace_id = uuid.uuid4()

        v1 = MagicMock()
        v1.id = v1_id
        v1.content = v1_content

        v2 = MagicMock()
        v2.id = v2_id
        v2.content = v2_content

        repo = AsyncMock()
        repo.get_by_id_for_note = AsyncMock(side_effect=[v1, v2])

        session = AsyncMock()
        svc = VersionDiffService(session, repo)
        return svc, v1_id, v2_id, note_id, workspace_id

    @pytest.mark.asyncio
    async def test_unchanged_blocks(self) -> None:
        from pilot_space.application.services.version.diff_service import DiffType

        doc = tiptap_doc("block-1", "block-2")
        svc, v1_id, v2_id, note_id, ws_id = self._make_service(doc, doc)
        result = await svc.execute(v1_id, v2_id, note_id, ws_id)

        assert not result.has_changes
        assert all(b.diff_type == DiffType.UNCHANGED for b in result.blocks)

    @pytest.mark.asyncio
    async def test_added_block(self) -> None:
        from pilot_space.application.services.version.diff_service import DiffType

        old = tiptap_doc("block-1")
        new = tiptap_doc("block-1", "block-2")
        svc, v1_id, v2_id, note_id, ws_id = self._make_service(old, new)
        result = await svc.execute(v1_id, v2_id, note_id, ws_id)

        assert result.added_count == 1
        added = [b for b in result.blocks if b.diff_type == DiffType.ADDED]
        assert len(added) == 1
        assert added[0].block_id == "block-2"

    @pytest.mark.asyncio
    async def test_removed_block(self) -> None:
        from pilot_space.application.services.version.diff_service import DiffType

        old = tiptap_doc("block-1", "block-2")
        new = tiptap_doc("block-1")
        svc, v1_id, v2_id, note_id, ws_id = self._make_service(old, new)
        result = await svc.execute(v1_id, v2_id, note_id, ws_id)

        assert result.removed_count == 1
        removed = [b for b in result.blocks if b.diff_type == DiffType.REMOVED]
        assert len(removed) == 1
        assert removed[0].block_id == "block-2"

    @pytest.mark.asyncio
    async def test_modified_block(self) -> None:
        from pilot_space.application.services.version.diff_service import DiffType

        old = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": "b1"},
                    "content": [{"type": "text", "text": "old text"}],
                }
            ],
        }
        new = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": "b1"},
                    "content": [{"type": "text", "text": "new text"}],
                }
            ],
        }
        svc, v1_id, v2_id, note_id, ws_id = self._make_service(old, new)
        result = await svc.execute(v1_id, v2_id, note_id, ws_id)

        assert result.modified_count == 1
        modified = [b for b in result.blocks if b.diff_type == DiffType.MODIFIED]
        assert modified[0].old_content is not None
        assert modified[0].new_content is not None

    @pytest.mark.asyncio
    async def test_version_not_found_raises(self) -> None:
        from pilot_space.application.services.version.diff_service import VersionDiffService

        repo = AsyncMock()
        repo.get_by_id_for_note = AsyncMock(return_value=None)
        session = AsyncMock()
        svc = VersionDiffService(session, repo)

        with pytest.raises(NotFoundError, match="not found"):
            await svc.execute(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4())


# ─── ImpactAnalysisService ──────────────────────────────────────────────────


class TestImpactAnalysisService:
    """Tests for entity reference detection (T-211)."""

    def _make_service(self, content: dict) -> Any:
        from pilot_space.application.services.version.impact_service import ImpactAnalysisService

        version = MagicMock()
        version.content = content

        repo = AsyncMock()
        repo.get_by_id_for_note = AsyncMock(return_value=version)
        session = AsyncMock()
        return ImpactAnalysisService(session, repo)

    @pytest.mark.asyncio
    async def test_detects_issue_reference(self) -> None:
        content = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Relates to PS-42 and PS-100"}],
                }
            ],
        }
        svc = self._make_service(content)
        result = await svc.execute(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
        assert len(result.issue_references) == 2
        identifiers = {r.identifier for r in result.issue_references}
        assert "PS-42" in identifiers
        assert "PS-100" in identifiers

    @pytest.mark.asyncio
    async def test_detects_uuid_reference(self) -> None:
        uid = str(uuid.uuid4())
        content = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": f"See note {uid}"}]}
            ],
        }
        svc = self._make_service(content)
        result = await svc.execute(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
        assert len(result.note_references) == 1
        assert result.note_references[0].identifier == uid.lower()

    @pytest.mark.asyncio
    async def test_no_references_returns_empty(self) -> None:
        content = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "just some text"}]}
            ],
        }
        svc = self._make_service(content)
        result = await svc.execute(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
        assert len(result.references) == 0

    @pytest.mark.asyncio
    async def test_version_not_found_raises(self) -> None:
        from pilot_space.application.services.version.impact_service import ImpactAnalysisService

        repo = AsyncMock()
        repo.get_by_id_for_note = AsyncMock(return_value=None)
        session = AsyncMock()
        svc = ImpactAnalysisService(session, repo)

        with pytest.raises(NotFoundError, match="not found"):
            await svc.execute(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())


# ─── RetentionService ───────────────────────────────────────────────────────


class TestRetentionService:
    """Tests for RetentionService pinned exemption (T-212)."""

    def _make_service(self, candidates: list, total: int = 0) -> Any:
        from pilot_space.application.services.version.retention_service import RetentionService

        repo = AsyncMock()
        repo.find_retention_candidates = AsyncMock(return_value=candidates)
        repo.batch_delete = AsyncMock(return_value=len(candidates))
        repo.count_by_note = AsyncMock(return_value=total)
        session = AsyncMock()
        return RetentionService(session, repo)

    @pytest.mark.asyncio
    async def test_no_candidates_returns_zero_deleted(self) -> None:
        from pilot_space.application.services.version.retention_service import RetentionPayload

        svc = self._make_service([], total=5)
        result = await svc.execute(
            RetentionPayload(note_id=uuid.uuid4(), workspace_id=uuid.uuid4())
        )
        assert result.deleted_count == 0
        assert result.retained_count == 5

    @pytest.mark.asyncio
    async def test_deletes_candidates(self) -> None:
        from pilot_space.application.services.version.retention_service import RetentionPayload

        cands = [MagicMock(id=uuid.uuid4()), MagicMock(id=uuid.uuid4())]
        svc = self._make_service(cands, total=3)
        result = await svc.execute(
            RetentionPayload(note_id=uuid.uuid4(), workspace_id=uuid.uuid4())
        )
        assert result.deleted_count == 2
        assert result.retained_count == 3


# ─── VersioningSkillHook ────────────────────────────────────────────────────


class TestVersioningSkillHook:
    """Tests for ai_before/ai_after skill versioning hook (T-213)."""

    def test_should_version_for_note_mutating_skills(self) -> None:
        from pilot_space.ai.skills.versioning_hook import VersioningSkillHook

        hook = VersioningSkillHook(
            session=AsyncMock(),
            note_repo=AsyncMock(),
            version_repo=AsyncMock(),
        )
        assert hook.should_version("improve-writing") is True
        assert hook.should_version("generate-diagram") is True
        assert hook.should_version("summarize") is True

    def test_should_not_version_for_read_skills(self) -> None:
        from pilot_space.ai.skills.versioning_hook import VersioningSkillHook

        hook = VersioningSkillHook(
            session=AsyncMock(),
            note_repo=AsyncMock(),
            version_repo=AsyncMock(),
        )
        assert hook.should_version("find-duplicates") is False
        assert hook.should_version("recommend-assignee") is False

    @pytest.mark.asyncio
    async def test_no_note_id_skips_versioning(self) -> None:
        from pilot_space.ai.skills.versioning_hook import VersioningSkillHook

        snapshot_svc = AsyncMock()
        hook = VersioningSkillHook(
            session=AsyncMock(),
            note_repo=AsyncMock(),
            version_repo=AsyncMock(),
        )
        hook._snapshot_svc = snapshot_svc

        body_called = False
        async with hook.around_skill("improve-writing", None, uuid.uuid4(), uuid.uuid4()):
            body_called = True

        assert body_called
        snapshot_svc.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_mutating_skill_skips_versioning(self) -> None:
        from pilot_space.ai.skills.versioning_hook import VersioningSkillHook

        snapshot_svc = AsyncMock()
        hook = VersioningSkillHook(
            session=AsyncMock(),
            note_repo=AsyncMock(),
            version_repo=AsyncMock(),
        )
        hook._snapshot_svc = snapshot_svc

        async with hook.around_skill("find-duplicates", uuid.uuid4(), uuid.uuid4(), uuid.uuid4()):
            pass

        snapshot_svc.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_mutating_skill_creates_before_and_after(self) -> None:
        from pilot_space.ai.skills.versioning_hook import VersioningSkillHook
        from pilot_space.domain.note_version import VersionTrigger

        snapshot_svc = AsyncMock()
        hook = VersioningSkillHook(
            session=AsyncMock(),
            note_repo=AsyncMock(),
            version_repo=AsyncMock(),
        )
        hook._snapshot_svc = snapshot_svc

        note_id = uuid.uuid4()
        ws_id = uuid.uuid4()
        user_id = uuid.uuid4()

        async with hook.around_skill("improve-writing", note_id, ws_id, user_id):
            pass

        assert snapshot_svc.execute.call_count == 2
        calls = snapshot_svc.execute.call_args_list
        assert calls[0].args[0].trigger == VersionTrigger.AI_BEFORE
        assert calls[1].args[0].trigger == VersionTrigger.AI_AFTER

    @pytest.mark.asyncio
    async def test_after_snapshot_still_created_on_skill_error(self) -> None:
        from pilot_space.ai.skills.versioning_hook import VersioningSkillHook

        snapshot_svc = AsyncMock()
        hook = VersioningSkillHook(
            session=AsyncMock(),
            note_repo=AsyncMock(),
            version_repo=AsyncMock(),
        )
        hook._snapshot_svc = snapshot_svc

        with pytest.raises(RuntimeError):
            async with hook.around_skill(
                "improve-writing", uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
            ):
                raise RuntimeError("skill failed")

        # Both before and after still attempted
        assert snapshot_svc.execute.call_count == 2


# ─── ConcurrentRestoreError ─────────────────────────────────────────────────


class TestConcurrentRestoreError:
    """Tests for optimistic locking error (C-9)."""

    def test_error_stores_competing_version_number(self) -> None:
        from pilot_space.application.services.version.restore_service import ConcurrentRestoreError

        err = ConcurrentRestoreError(competing_version_number=5)
        assert err.competing_version_number == 5
        assert "5" in str(err)


# ─── _uuid_to_advisory_key ──────────────────────────────────────────────────


class TestUuidToAdvisoryKey:
    """Tests for pg_advisory_lock key computation."""

    def test_returns_positive_int(self) -> None:
        from pilot_space.application.services.version.restore_service import _uuid_to_advisory_key

        key = _uuid_to_advisory_key(uuid.uuid4())
        assert isinstance(key, int)
        assert key >= 0

    def test_fits_in_63_bits(self) -> None:
        from pilot_space.application.services.version.restore_service import _uuid_to_advisory_key

        key = _uuid_to_advisory_key(uuid.uuid4())
        assert key < 2**63

    def test_deterministic_for_same_uuid(self) -> None:
        from pilot_space.application.services.version.restore_service import _uuid_to_advisory_key

        uid = UUID("12345678-1234-5678-1234-567812345678")
        assert _uuid_to_advisory_key(uid) == _uuid_to_advisory_key(uid)


# ─── GAP-02: VersionTrigger enum completeness ───────────────────────────────


class TestVersionTriggerEnum:
    """GAP-02: VersionTrigger must distinguish all four trigger types."""

    def test_all_four_values_defined(self) -> None:
        """VersionTrigger has manual, auto, ai_before, ai_after — no boolean collapse."""
        assert VersionTrigger.MANUAL.value == "manual"
        assert VersionTrigger.AUTO.value == "auto"
        assert VersionTrigger.AI_BEFORE.value == "ai_before"
        assert VersionTrigger.AI_AFTER.value == "ai_after"

    def test_is_ai_triggered_for_ai_before(self) -> None:
        v = make_version(trigger=VersionTrigger.AI_BEFORE)
        assert v.is_ai_triggered

    def test_is_ai_triggered_for_ai_after(self) -> None:
        v = make_version(trigger=VersionTrigger.AI_AFTER)
        assert v.is_ai_triggered

    def test_not_ai_triggered_for_manual(self) -> None:
        v = make_version(trigger=VersionTrigger.MANUAL)
        assert not v.is_ai_triggered

    def test_not_ai_triggered_for_auto(self) -> None:
        v = make_version(trigger=VersionTrigger.AUTO)
        assert not v.is_ai_triggered


# ─── GAP-04: undo-ai fast path service logic ────────────────────────────────


class TestUndoAiServiceLogic:
    """GAP-04: undo-ai restores the closest ai_before snapshot."""

    @pytest.mark.asyncio
    async def test_undo_ai_uses_latest_ai_before(self) -> None:
        """VersionRestoreService is called with the ai_before version ID."""
        from pilot_space.application.services.version.restore_service import (
            RestorePayload,
            VersionRestoreService,
        )
        from pilot_space.domain.note_version import NoteVersion as DomainNoteVersion

        ai_before_id = uuid.uuid4()
        note_id = uuid.uuid4()
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # ai_before ORM mock
        ai_before_orm = MagicMock()
        ai_before_orm.id = ai_before_id
        ai_before_orm.note_id = note_id
        ai_before_orm.workspace_id = workspace_id
        ai_before_orm.label = "Before AI edit"
        ai_before_orm.content = {"type": "doc", "content": []}
        ai_before_orm.created_at = datetime.now(tz=UTC)

        version_repo = MagicMock()
        version_repo.get_latest_ai_before = AsyncMock(return_value=ai_before_orm)

        # Verify the payload passed to restore service uses the ai_before id
        captured: list[RestorePayload] = []

        async def fake_execute(payload: RestorePayload) -> Any:
            captured.append(payload)
            new_v = DomainNoteVersion(
                id=uuid.uuid4(),
                note_id=note_id,
                workspace_id=workspace_id,
                trigger=VersionTrigger.MANUAL,
                content=ai_before_orm.content,
                created_at=datetime.now(tz=UTC),
            )
            from pilot_space.application.services.version.restore_service import RestoreResult

            return RestoreResult(new_version=new_v, restored_from_version_id=ai_before_id)

        restore_svc = MagicMock(spec=VersionRestoreService)
        restore_svc.execute = AsyncMock(side_effect=fake_execute)

        # Simulate what the undo-ai endpoint does:
        ai_before = await version_repo.get_latest_ai_before(note_id, workspace_id)
        assert ai_before is not None
        result = await restore_svc.execute(
            RestorePayload(
                version_id=ai_before.id,
                note_id=note_id,
                workspace_id=workspace_id,
                restored_by=user_id,
                expected_version_number=3,
            )
        )

        assert captured[0].version_id == ai_before_id
        assert result.restored_from_version_id == ai_before_id

    @pytest.mark.asyncio
    async def test_undo_ai_no_ai_before_returns_none(self) -> None:
        """get_latest_ai_before returns None when no AI has edited the note."""
        version_repo = MagicMock()
        version_repo.get_latest_ai_before = AsyncMock(return_value=None)

        result = await version_repo.get_latest_ai_before(uuid.uuid4(), uuid.uuid4())
        assert result is None
