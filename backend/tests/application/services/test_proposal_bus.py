"""Tests for ProposalBus — status transitions + SSE/executor seams.

Uses a real ``ProposalRepository`` bound to the SQLite ``db_session`` fixture
so state persists across bus calls in a single test. SSE publisher and intent
executor are mocked — their real wiring lands in Plans 02 and 03.

Status-transition state machine asserted:
    PENDING --accept--> APPLIED   (executor success path)
    PENDING --accept--> ERRORED   (executor raises)
    PENDING --reject--> REJECTED
    PENDING --retry-->  RETRIED
    !PENDING --any-->   ProposalAlreadyDecidedError
    missing id -->      ProposalNotFoundError
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.proposal_bus import (
    IntentExecutionOutcome,
    ProposalAlreadyDecidedError,
    ProposalApplyResult,
    ProposalBus,
    ProposalIntentExecutionError,
    ProposalNotFoundError,
)
from pilot_space.application.services.proposal_repository import ProposalRepository
from pilot_space.domain.exceptions import AppError, ConflictError, NotFoundError
from pilot_space.domain.proposal import (
    ArtifactType,
    ChatMode,
    DiffKind,
    Proposal,
    ProposalStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sse_mock() -> AsyncMock:
    mock = AsyncMock()
    mock.publish_proposal_request = AsyncMock()
    mock.publish_proposal_applied = AsyncMock()
    mock.publish_proposal_rejected = AsyncMock()
    mock.publish_proposal_retried = AsyncMock()
    return mock


def _make_executor_mock(*, outcome: IntentExecutionOutcome | None = None) -> AsyncMock:
    mock = AsyncMock()
    if outcome is not None:
        mock.execute = AsyncMock(return_value=outcome)
    else:
        mock.execute = AsyncMock(
            return_value=IntentExecutionOutcome(applied_version=2, lines_changed=14)
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


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_not_found_extends_app_error_404(self) -> None:
        exc = ProposalNotFoundError("x")
        assert isinstance(exc, NotFoundError)
        assert isinstance(exc, AppError)
        assert exc.http_status == 404
        assert exc.error_code == "proposal_not_found"

    def test_already_decided_extends_conflict_409(self) -> None:
        exc = ProposalAlreadyDecidedError("x")
        assert isinstance(exc, ConflictError)
        assert exc.http_status == 409
        assert exc.error_code == "proposal_already_decided"

    def test_intent_exec_extends_app_error_502(self) -> None:
        exc = ProposalIntentExecutionError("x")
        assert isinstance(exc, AppError)
        assert exc.http_status == 502
        assert exc.error_code == "proposal_intent_execution_failed"


# ---------------------------------------------------------------------------
# Create — SSE publication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCreate:
    async def test_create_persists_pending_and_publishes_request(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        sse = _make_sse_mock()
        bus = ProposalBus(repository=repo, sse_publisher=sse)

        proposal = await bus.create_proposal(
            workspace_id=uuid4(),
            session_id=uuid4(),
            message_id=uuid4(),
            target_artifact_type=ArtifactType.NOTE,
            target_artifact_id=uuid4(),
            intent_tool="update_note_content",
            intent_args={"text": "x"},
            diff_kind=DiffKind.TEXT,
            diff_payload={"before": "a", "after": "b"},
            reasoning="rename",
            mode=ChatMode.ACT,
        )
        assert proposal.status == ProposalStatus.PENDING
        sse.publish_proposal_request.assert_awaited_once()
        (arg,), _ = sse.publish_proposal_request.call_args
        assert arg.id == proposal.id


# ---------------------------------------------------------------------------
# Accept
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAccept:
    async def test_accept_pending_executes_and_marks_applied(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        sse = _make_sse_mock()
        executor = _make_executor_mock(
            outcome=IntentExecutionOutcome(applied_version=3, lines_changed=7)
        )
        bus = ProposalBus(repository=repo, sse_publisher=sse, intent_executor=executor)

        pending = await _seed_pending(repo)
        decided_by = uuid4()
        result = await bus.accept_proposal(pending.id, decided_by=decided_by)

        assert isinstance(result, ProposalApplyResult)
        assert result.proposal.status == ProposalStatus.APPLIED
        assert result.applied_version == 3
        assert result.lines_changed == 7
        executor.execute.assert_awaited_once()
        sse.publish_proposal_applied.assert_awaited_once()

    async def test_accept_missing_raises_not_found(
        self, db_session: AsyncSession
    ) -> None:
        bus = ProposalBus(
            repository=ProposalRepository(db_session),
            sse_publisher=_make_sse_mock(),
            intent_executor=_make_executor_mock(),
        )
        with pytest.raises(ProposalNotFoundError):
            await bus.accept_proposal(uuid4(), decided_by=uuid4())

    async def test_accept_already_applied_raises_conflict(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        executor = _make_executor_mock()
        bus = ProposalBus(
            repository=repo, sse_publisher=_make_sse_mock(), intent_executor=executor
        )
        pending = await _seed_pending(repo)
        await bus.accept_proposal(pending.id, decided_by=uuid4())
        with pytest.raises(ProposalAlreadyDecidedError):
            await bus.accept_proposal(pending.id, decided_by=uuid4())

    async def test_accept_executor_failure_marks_errored_and_raises(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        sse = _make_sse_mock()
        executor = AsyncMock()
        executor.execute = AsyncMock(side_effect=RuntimeError("boom"))
        bus = ProposalBus(repository=repo, sse_publisher=sse, intent_executor=executor)

        pending = await _seed_pending(repo)
        with pytest.raises(ProposalIntentExecutionError):
            await bus.accept_proposal(pending.id, decided_by=uuid4())

        reloaded = await repo.get_by_id(pending.id)
        assert reloaded is not None
        assert reloaded.status == ProposalStatus.ERRORED
        sse.publish_proposal_applied.assert_not_awaited()


# ---------------------------------------------------------------------------
# Reject / Retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRejectRetry:
    async def test_reject_pending_marks_rejected_and_publishes(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        sse = _make_sse_mock()
        bus = ProposalBus(repository=repo, sse_publisher=sse)
        pending = await _seed_pending(repo)

        result = await bus.reject_proposal(
            pending.id, decided_by=uuid4(), reason="off-topic"
        )
        assert result.status == ProposalStatus.REJECTED
        sse.publish_proposal_rejected.assert_awaited_once()

    async def test_retry_pending_marks_retried_and_publishes(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        sse = _make_sse_mock()
        bus = ProposalBus(repository=repo, sse_publisher=sse)
        pending = await _seed_pending(repo)

        result = await bus.retry_proposal(
            pending.id, decided_by=uuid4(), hint="narrow scope"
        )
        assert result.status == ProposalStatus.RETRIED
        sse.publish_proposal_retried.assert_awaited_once()

    async def test_reject_already_decided_raises(
        self, db_session: AsyncSession
    ) -> None:
        repo = ProposalRepository(db_session)
        bus = ProposalBus(repository=repo, sse_publisher=_make_sse_mock())
        pending = await _seed_pending(repo)
        await bus.reject_proposal(pending.id, decided_by=uuid4(), reason=None)
        with pytest.raises(ProposalAlreadyDecidedError):
            await bus.reject_proposal(pending.id, decided_by=uuid4(), reason=None)


# ---------------------------------------------------------------------------
# DI smoke test
# ---------------------------------------------------------------------------


def test_container_resolves_proposal_bus_and_repository() -> None:
    """Smoke test: Container() can resolve proposal_bus without error.

    Exercises wiring config + factory providers without touching a real DB —
    we seed the request-scoped session ContextVar so ``get_current_session``
    yields a fake AsyncSession.
    """
    import pilot_space.dependencies.auth as auth_mod
    from pilot_space.container.container import Container

    container = Container()
    fake_session: Any = AsyncMock(spec=AsyncSession)
    token = auth_mod._request_session_ctx.set(fake_session)
    try:
        repo = container.proposal_repository()
        bus = container.proposal_bus()
        assert isinstance(repo, ProposalRepository)
        assert isinstance(bus, ProposalBus)
    finally:
        auth_mod._request_session_ctx.reset(token)
