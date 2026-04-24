"""Tests for ``ProposalBus.revert_proposal`` (Phase 89 Plan 05 Task 1).

Covers:

* APPLIED -> revert success path: delegates to ``IntentExecutor.execute_revert``
  with ``(target_artifact_type, target_artifact_id, workspace_id)`` and emits
  ``publish_proposal_reverted`` with the new + prior version numbers.
* Window enforcement: ``decided_at + 10min < now`` -> ``ProposalCannotBeRevertedError``
  (409, error_code=``proposal_cannot_be_reverted``).
* Status gating: PENDING / REJECTED / RETRIED / ERRORED proposals cannot be
  reverted -> 409.
* Missing proposal -> ``ProposalNotFoundError`` (404).
* Original proposal row's ``status`` is NOT mutated by revert — revert is a
  new versioned mutation on the artifact, not a state change on the proposal.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.proposal_bus import (
    IntentExecutionOutcome,
    ProposalBus,
    ProposalCannotBeRevertedError,
    ProposalNotFoundError,
    RevertResult,
)
from pilot_space.application.services.proposal_repository import ProposalRepository
from pilot_space.domain.exceptions import AppError, ConflictError
from pilot_space.domain.proposal import (
    ArtifactType,
    ChatMode,
    DiffKind,
    Proposal,
    ProposalStatus,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sse_mock() -> AsyncMock:
    mock = AsyncMock()
    mock.publish_proposal_request = AsyncMock()
    mock.publish_proposal_applied = AsyncMock()
    mock.publish_proposal_rejected = AsyncMock()
    mock.publish_proposal_retried = AsyncMock()
    mock.publish_proposal_reverted = AsyncMock()
    return mock


def _make_executor_mock(
    *,
    execute_outcome: IntentExecutionOutcome | None = None,
    revert_outcome: IntentExecutionOutcome | None = None,
) -> AsyncMock:
    mock = AsyncMock()
    mock.execute = AsyncMock(
        return_value=execute_outcome
        or IntentExecutionOutcome(applied_version=2, lines_changed=None)
    )
    mock.execute_revert = AsyncMock(
        return_value=revert_outcome
        or IntentExecutionOutcome(applied_version=3, lines_changed=None)
    )
    return mock


async def _seed_pending(repo: ProposalRepository) -> Proposal:
    return await repo.create(
        workspace_id=uuid4(),
        session_id=uuid4(),
        message_id=uuid4(),
        target_artifact_type=ArtifactType.ISSUE,
        target_artifact_id=uuid4(),
        intent_tool="update_issue",
        intent_args={"priority": "high"},
        diff_kind=DiffKind.FIELDS,
        diff_payload={"priority": {"from": "low", "to": "high"}},
        reasoning=None,
        mode=ChatMode.ACT,
    )


async def _seed_applied(
    repo: ProposalRepository, *, decided_at: datetime | None = None
) -> Proposal:
    """Create and apply a proposal; optionally override decided_at."""
    pending = await _seed_pending(repo)
    return await repo.update_status(
        pending.id,
        status=ProposalStatus.APPLIED,
        decided_by=uuid4(),
        decided_at=decided_at or datetime.now(UTC),
        applied_version=2,
    )


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_cannot_be_reverted_extends_conflict_409(self) -> None:
        exc = ProposalCannotBeRevertedError("x")
        assert isinstance(exc, ConflictError)
        assert isinstance(exc, AppError)
        assert exc.http_status == 409
        assert exc.error_code == "proposal_cannot_be_reverted"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRevertHappyPath:
    async def test_applied_within_window_reverts_and_publishes(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        sse = _make_sse_mock()
        # Executor returns applied_version=3 (new), previous was 2 so
        # reverted_from_version = 2.
        executor = _make_executor_mock(
            revert_outcome=IntentExecutionOutcome(applied_version=3, lines_changed=None)
        )
        bus = ProposalBus(
            repository=repo, sse_publisher=sse, intent_executor=executor
        )
        applied = await _seed_applied(repo)

        result = await bus.revert_proposal(applied.id, decided_by=uuid4())

        assert isinstance(result, RevertResult)
        assert result.new_version_number == 3
        assert result.proposal.id == applied.id
        # Executor invoked with per-artifact revert contract (no intent_tool, no intent_args).
        executor.execute_revert.assert_awaited_once()
        call_kwargs = executor.execute_revert.call_args.kwargs
        assert call_kwargs["target_artifact_type"] == applied.target_artifact_type
        assert call_kwargs["target_artifact_id"] == applied.target_artifact_id
        assert call_kwargs["workspace_id"] == applied.workspace_id
        # SSE publish on revert.
        sse.publish_proposal_reverted.assert_awaited_once()
        pub_kwargs = sse.publish_proposal_reverted.call_args.kwargs
        assert pub_kwargs["new_version_number"] == 3
        assert pub_kwargs["reverted_from_version"] == 2

    async def test_original_proposal_status_unchanged_after_revert(
        self, db_session: AsyncSession
    ) -> None:
        """Revert is a new versioned mutation on the artifact — the proposal
        row's status stays APPLIED. This is the architectural invariant per
        plan-notes_for_executor: "proposal pipeline records intents; the
        artifact records state".
        """
        repo = ProposalRepository(db_session)
        executor = _make_executor_mock()
        bus = ProposalBus(
            repository=repo,
            sse_publisher=_make_sse_mock(),
            intent_executor=executor,
        )
        applied = await _seed_applied(repo)

        await bus.revert_proposal(applied.id, decided_by=uuid4())

        reloaded = await repo.get_by_id(applied.id)
        assert reloaded is not None
        assert reloaded.status == ProposalStatus.APPLIED


# ---------------------------------------------------------------------------
# Window enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRevertWindow:
    async def test_outside_10min_window_raises_cannot_be_reverted(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        executor = _make_executor_mock()
        bus = ProposalBus(
            repository=repo,
            sse_publisher=_make_sse_mock(),
            intent_executor=executor,
        )
        # Decided 11 minutes ago — outside the 10-minute window.
        stale_decided_at = datetime.now(UTC) - timedelta(minutes=11)
        applied = await _seed_applied(repo, decided_at=stale_decided_at)

        with pytest.raises(ProposalCannotBeRevertedError) as exc_info:
            await bus.revert_proposal(applied.id, decided_by=uuid4())
        assert "window" in str(exc_info.value).lower()
        # Executor must not have been called when window is expired.
        executor.execute_revert.assert_not_awaited()

    async def test_within_10min_window_boundary_allows_revert(
        self, db_session: AsyncSession
    ) -> None:
        """9m59s after decided_at is still within window (boundary check)."""
        repo = ProposalRepository(db_session)
        executor = _make_executor_mock()
        bus = ProposalBus(
            repository=repo,
            sse_publisher=_make_sse_mock(),
            intent_executor=executor,
        )
        recent_decided_at = datetime.now(UTC) - timedelta(minutes=9, seconds=59)
        applied = await _seed_applied(repo, decided_at=recent_decided_at)

        result = await bus.revert_proposal(applied.id, decided_by=uuid4())
        assert result is not None


# ---------------------------------------------------------------------------
# Status gating
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRevertStatusGate:
    async def test_pending_cannot_be_reverted(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        bus = ProposalBus(
            repository=repo,
            sse_publisher=_make_sse_mock(),
            intent_executor=_make_executor_mock(),
        )
        pending = await _seed_pending(repo)

        with pytest.raises(ProposalCannotBeRevertedError):
            await bus.revert_proposal(pending.id, decided_by=uuid4())

    async def test_rejected_cannot_be_reverted(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        bus = ProposalBus(
            repository=repo,
            sse_publisher=_make_sse_mock(),
            intent_executor=_make_executor_mock(),
        )
        pending = await _seed_pending(repo)
        await repo.update_status(
            pending.id,
            status=ProposalStatus.REJECTED,
            decided_by=uuid4(),
            decided_at=datetime.now(UTC),
        )

        with pytest.raises(ProposalCannotBeRevertedError):
            await bus.revert_proposal(pending.id, decided_by=uuid4())

    async def test_retried_cannot_be_reverted(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        bus = ProposalBus(
            repository=repo,
            sse_publisher=_make_sse_mock(),
            intent_executor=_make_executor_mock(),
        )
        pending = await _seed_pending(repo)
        await repo.update_status(
            pending.id,
            status=ProposalStatus.RETRIED,
            decided_by=uuid4(),
            decided_at=datetime.now(UTC),
        )

        with pytest.raises(ProposalCannotBeRevertedError):
            await bus.revert_proposal(pending.id, decided_by=uuid4())

    async def test_errored_cannot_be_reverted(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        bus = ProposalBus(
            repository=repo,
            sse_publisher=_make_sse_mock(),
            intent_executor=_make_executor_mock(),
        )
        pending = await _seed_pending(repo)
        await repo.update_status(
            pending.id,
            status=ProposalStatus.ERRORED,
            decided_by=uuid4(),
            decided_at=datetime.now(UTC),
        )

        with pytest.raises(ProposalCannotBeRevertedError):
            await bus.revert_proposal(pending.id, decided_by=uuid4())


# ---------------------------------------------------------------------------
# Missing id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRevertMissing:
    async def test_missing_id_raises_not_found(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        bus = ProposalBus(
            repository=repo,
            sse_publisher=_make_sse_mock(),
            intent_executor=_make_executor_mock(),
        )

        with pytest.raises(ProposalNotFoundError):
            await bus.revert_proposal(uuid4(), decided_by=uuid4())


# ---------------------------------------------------------------------------
# Executor propagation — unlike accept_proposal, executor failures on revert
# should propagate cleanly (no ERRORED-status side-effect on the proposal row,
# per "revert does not mutate proposal status" invariant).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRevertExecutorFailure:
    async def test_executor_failure_propagates_and_leaves_status_applied(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        executor = AsyncMock()
        executor.execute_revert = AsyncMock(side_effect=RuntimeError("oops"))
        bus = ProposalBus(
            repository=repo, sse_publisher=_make_sse_mock(), intent_executor=executor
        )
        applied = await _seed_applied(repo)

        with pytest.raises(RuntimeError, match="oops"):
            await bus.revert_proposal(applied.id, decided_by=uuid4())

        reloaded = await repo.get_by_id(applied.id)
        assert reloaded is not None
        assert reloaded.status == ProposalStatus.APPLIED


# Silence ruff for this file — tests intentionally import Any if extended later.
_ = Any
