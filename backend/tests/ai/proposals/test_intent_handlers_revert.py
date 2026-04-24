"""Tests for per-artifact revert handlers (Phase 89 Plan 05 Task 1).

Scope covered:

* ``IntentExecutor.execute_revert`` dispatches to ``_REVERT_REGISTRY`` by
  ``ArtifactType`` (NOT tool name — revert is per-artifact).
* ``register_revert`` decorator populates the registry keyed by artifact.
* ``revert_issue`` restores the prior snapshot from ``version_history[-1]``,
  bumps ``version_number``, appends a new ``by:'user'`` entry — append-only.
* ``revert_note`` reads the latest ``ai_before`` NoteVersion snapshot and
  restores ``note.content`` without mutating older NoteVersion rows (reuses
  existing infra — no JSONB duplication).
* ``revert_spec`` / ``revert_decision`` — NOT registered (tables deferred
  per Plan 01 D-89-01-02 / Plan 03 D-89-03-06); dispatch raises
  ``IntentNotRegisteredError``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.ai.proposals.intent_executor import (
    _REVERT_REGISTRY,
    IntentExecutor,
    IntentNotRegisteredError,
    register_revert,
)
from pilot_space.application.services.proposal_bus import IntentExecutionOutcome
from pilot_space.dependencies.auth import _request_session_ctx as session_ctx
from pilot_space.domain.proposal import ArtifactType
from pilot_space.infrastructure.database.models import Issue, Note
from pilot_space.infrastructure.database.models.issue import IssuePriority
from pilot_space.infrastructure.database.models.note_version import (
    NoteVersion,
    VersionTrigger,
)

# ---------------------------------------------------------------------------
# Registry & dispatcher
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _preserve_revert_registry():
    """Snapshot revert registry so per-test registrations don't leak."""
    snapshot = dict(_REVERT_REGISTRY)
    yield
    _REVERT_REGISTRY.clear()
    _REVERT_REGISTRY.update(snapshot)


@pytest.mark.asyncio
async def test_register_revert_populates_registry_by_artifact_type() -> None:
    # Isolate: clear the real registration before asserting our handler wins.
    _REVERT_REGISTRY.pop(ArtifactType.ISSUE, None)

    @register_revert(ArtifactType.ISSUE)
    async def _fake_revert(*, workspace_id, target_artifact_id):
        return IntentExecutionOutcome(applied_version=99)

    assert _REVERT_REGISTRY[ArtifactType.ISSUE] is _fake_revert


@pytest.mark.asyncio
async def test_execute_revert_dispatches_to_registered_handler() -> None:
    captured: dict[str, object] = {}

    @register_revert(ArtifactType.DECISION)  # use DECISION to avoid clobbering real handlers
    async def _handler(*, workspace_id, target_artifact_id):
        captured["workspace_id"] = workspace_id
        captured["target_artifact_id"] = target_artifact_id
        return IntentExecutionOutcome(applied_version=5)

    workspace_id = uuid4()
    target_id = uuid4()

    outcome = await IntentExecutor().execute_revert(
        target_artifact_type=ArtifactType.DECISION,
        target_artifact_id=target_id,
        workspace_id=workspace_id,
    )

    assert outcome.applied_version == 5
    assert captured == {
        "workspace_id": workspace_id,
        "target_artifact_id": target_id,
    }


@pytest.mark.asyncio
async def test_execute_revert_unknown_artifact_raises() -> None:
    # SPEC is not registered — defer per Plan 03 D-89-03-06.
    with pytest.raises(IntentNotRegisteredError):
        await IntentExecutor().execute_revert(
            target_artifact_type=ArtifactType.SPEC,
            target_artifact_id=uuid4(),
            workspace_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_real_revert_registry_after_import_contains_issue_and_note() -> None:
    import pilot_space.ai.proposals  # noqa: F401 — side-effect import

    assert ArtifactType.ISSUE in _REVERT_REGISTRY
    assert ArtifactType.NOTE in _REVERT_REGISTRY
    # Spec + Decision are deferred and NOT registered.
    assert ArtifactType.SPEC not in _REVERT_REGISTRY
    assert ArtifactType.DECISION not in _REVERT_REGISTRY


# ---------------------------------------------------------------------------
# Issue revert — restores prior snapshot, bumps version, appends by:'user'.
# ---------------------------------------------------------------------------


async def _seed_issue_with_history(
    db_session: AsyncSession,
    workspace_id: UUID,
    *,
    current_name: str,
    prior_snapshot: dict[str, Any],
    current_version: int = 2,
) -> Issue:
    """Create an Issue row with version_history containing ONE prior entry.

    Seeds a minimal project row, then attaches the issue. Issue starts at
    ``current_version``; ``version_history[-1]`` contains the pre-mutation
    snapshot (what we revert to).
    """
    from pilot_space.infrastructure.database.models import Project
    from pilot_space.infrastructure.database.models.state import State, StateGroup

    reporter_id = uuid4()
    project_id = uuid4()
    state_id = uuid4()

    project = Project(
        id=project_id,
        workspace_id=workspace_id,
        name="Test Project",
        identifier="TST",
    )
    db_session.add(project)

    state = State(
        id=state_id,
        workspace_id=workspace_id,
        project_id=project_id,
        name="Todo",
        group=StateGroup.UNSTARTED,
        color="#888",
        sequence=0,
    )
    db_session.add(state)

    issue = Issue(
        id=uuid4(),
        workspace_id=workspace_id,
        project_id=project_id,
        reporter_id=reporter_id,
        state_id=state_id,
        sequence_id=1,
        name=current_name,
        description="current desc",
        priority=IssuePriority.HIGH,
        version_number=current_version,
        version_history=[
            {
                "vN": current_version - 1,
                "by": "ai",
                "at": datetime.now(UTC).isoformat(),
                "summary": "AI updated: title, description",
                "snapshot": prior_snapshot,
            }
        ],
    )
    db_session.add(issue)
    await db_session.flush()
    return issue


@pytest.mark.asyncio
async def test_revert_issue_restores_prior_snapshot_and_bumps_version(
    db_session: AsyncSession,
) -> None:
    # Import triggers @register_revert side effect.
    import pilot_space.ai.proposals.intent_handlers.issue  # noqa: F401

    token = session_ctx.set(db_session)
    try:
        workspace_id = uuid4()
        prior_snapshot = {
            "name": "Original title",
            "description": "Original description",
            "priority": "medium",
            "assignee_id": None,
            "estimate_points": None,
            "start_date": None,
            "target_date": None,
        }
        issue = await _seed_issue_with_history(
            db_session,
            workspace_id,
            current_name="AI-edited title",
            prior_snapshot=prior_snapshot,
            current_version=2,
        )
        # History integrity marker — we'll confirm this entry is unchanged.
        prior_history_first_entry = dict(issue.version_history[0])

        outcome = await IntentExecutor().execute_revert(
            target_artifact_type=ArtifactType.ISSUE,
            target_artifact_id=issue.id,
            workspace_id=workspace_id,
        )

        assert outcome.applied_version == 3  # bumped from 2
        await db_session.refresh(issue)
        # Fields restored from snapshot.
        assert issue.name == "Original title"
        assert issue.description == "Original description"
        assert issue.priority == IssuePriority.MEDIUM
        assert issue.version_number == 3
        # Append-only: prior entry untouched + new entry appended with by:'user'.
        assert len(issue.version_history) == 2
        assert issue.version_history[0] == prior_history_first_entry
        new_entry = issue.version_history[-1]
        assert new_entry["by"] == "user"
        assert new_entry["vN"] == 2  # snapshots the pre-revert state
        assert "Reverted" in new_entry["summary"]
    finally:
        session_ctx.reset(token)


@pytest.mark.asyncio
async def test_revert_issue_with_empty_history_raises(
    db_session: AsyncSession,
) -> None:
    """An Issue never edited by AI has an empty version_history; revert is nonsensical."""
    import pilot_space.ai.proposals.intent_handlers.issue  # noqa: F401
    from pilot_space.application.services.proposal_bus import (
        ProposalCannotBeRevertedError,
    )
    from pilot_space.infrastructure.database.models import Project
    from pilot_space.infrastructure.database.models.state import State, StateGroup

    token = session_ctx.set(db_session)
    try:
        workspace_id = uuid4()
        project_id = uuid4()
        state_id = uuid4()
        db_session.add(Project(id=project_id, workspace_id=workspace_id, name="P", identifier="P"))
        db_session.add(
            State(
                id=state_id,
                workspace_id=workspace_id,
                project_id=project_id,
                name="Todo",
                group=StateGroup.UNSTARTED,
                color="#888",
                sequence=0,
            )
        )
        issue = Issue(
            id=uuid4(),
            workspace_id=workspace_id,
            project_id=project_id,
            reporter_id=uuid4(),
            state_id=state_id,
            sequence_id=1,
            name="Fresh",
            priority=IssuePriority.MEDIUM,
            version_number=1,
            version_history=[],
        )
        db_session.add(issue)
        await db_session.flush()

        with pytest.raises(ProposalCannotBeRevertedError):
            await IntentExecutor().execute_revert(
                target_artifact_type=ArtifactType.ISSUE,
                target_artifact_id=issue.id,
                workspace_id=workspace_id,
            )
    finally:
        session_ctx.reset(token)


# ---------------------------------------------------------------------------
# Note revert — reuses note_versions table (no version_history JSONB).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revert_note_restores_from_latest_ai_before_snapshot(
    db_session: AsyncSession,
) -> None:
    """Note revert reuses ``NoteVersionRepository.get_latest_ai_before`` — the
    handler restores ``note.content`` from the snapshot and appends a new
    NoteVersion row tagged ``MANUAL`` with a ``'user revert'`` label.
    """
    import pilot_space.ai.proposals.intent_handlers.note  # noqa: F401

    token = session_ctx.set(db_session)
    try:
        workspace_id = uuid4()
        owner_id = uuid4()

        # Seed a note with CURRENT content (post-AI-edit state).
        note = Note(
            id=uuid4(),
            workspace_id=workspace_id,
            owner_id=owner_id,
            title="Draft",
            content={"type": "doc", "content": [{"type": "paragraph", "text": "AI rewrote this"}]},
        )
        db_session.add(note)

        # Seed an ai_before NoteVersion carrying the PRIOR content.
        prior_content = {"type": "doc", "content": [{"type": "paragraph", "text": "Original"}]}
        ai_before = NoteVersion(
            id=uuid4(),
            note_id=note.id,
            workspace_id=workspace_id,
            trigger=VersionTrigger.AI_BEFORE,
            content=prior_content,
            version_number=1,
        )
        db_session.add(ai_before)
        await db_session.flush()

        outcome = await IntentExecutor().execute_revert(
            target_artifact_type=ArtifactType.NOTE,
            target_artifact_id=note.id,
            workspace_id=workspace_id,
        )

        assert outcome.applied_version >= 1
        await db_session.refresh(note)
        assert note.content == prior_content

        # The prior ai_before row MUST be untouched (append-only invariant).
        await db_session.refresh(ai_before)
        assert ai_before.content == prior_content

        # A new NoteVersion snapshot must have been appended (MANUAL trigger,
        # user revert label).
        from sqlalchemy import select

        rows = await db_session.execute(
            select(NoteVersion).where(
                NoteVersion.note_id == note.id,
                NoteVersion.trigger == VersionTrigger.MANUAL,
            )
        )
        reverts = list(rows.scalars().all())
        assert len(reverts) == 1
        assert "revert" in (reverts[0].label or "").lower()
    finally:
        session_ctx.reset(token)


@pytest.mark.asyncio
async def test_revert_note_without_ai_before_raises(
    db_session: AsyncSession,
) -> None:
    """A Note with no ai_before snapshot has no prior state to revert to."""
    import pilot_space.ai.proposals.intent_handlers.note  # noqa: F401
    from pilot_space.application.services.proposal_bus import (
        ProposalCannotBeRevertedError,
    )

    token = session_ctx.set(db_session)
    try:
        workspace_id = uuid4()
        note = Note(
            id=uuid4(),
            workspace_id=workspace_id,
            owner_id=uuid4(),
            title="Fresh note",
            content={"type": "doc", "content": []},
        )
        db_session.add(note)
        await db_session.flush()

        with pytest.raises(ProposalCannotBeRevertedError):
            await IntentExecutor().execute_revert(
                target_artifact_type=ArtifactType.NOTE,
                target_artifact_id=note.id,
                workspace_id=workspace_id,
            )
    finally:
        session_ctx.reset(token)


# Silence ruff
_ = uuid, date
