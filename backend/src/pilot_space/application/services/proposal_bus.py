"""ProposalBus — status-transition orchestrator for the Edit Proposal pipeline.

Phase 89 Plan 01 ships the skeleton: persistence + status state machine + SSE
publisher seam + IntentExecutor seam. Real SSE publication lands in Plan 02
(`ChatStreamPublisher`); real intent execution lands in Plan 03
(`IntentExecutor` + per-artifact handlers).

State machine (enforced here):
    PENDING --create-->        PENDING   (create_proposal)
    PENDING --accept (ok)-->   APPLIED   (accept_proposal)
    PENDING --accept (fail)--> ERRORED   (accept_proposal — executor raised)
    PENDING --reject-->        REJECTED  (reject_proposal)
    PENDING --retry-->         RETRIED   (retry_proposal)
    NOT PENDING --any-->       ProposalAlreadyDecidedError

Missing id -> ProposalNotFoundError (404). Executor failures surface as
ProposalIntentExecutionError (502) after persisting status=ERRORED.

Dependency surface kept minimal: only ProposalRepository is required. SSE
publisher + intent executor default to no-op / raising stubs so this module
is usable from Plan 02 before Plan 03 lands.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

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
# Exceptions (AppError subclasses — global handler converts to RFC 7807)
# ---------------------------------------------------------------------------


class ProposalNotFoundError(NotFoundError):
    """Proposal id does not exist."""

    error_code = "proposal_not_found"


class ProposalAlreadyDecidedError(ConflictError):
    """Proposal is no longer PENDING — cannot transition again."""

    error_code = "proposal_already_decided"


class ProposalIntentExecutionError(AppError):
    """The queued intent failed during apply — proposal marked ERRORED."""

    error_code = "proposal_intent_execution_failed"
    http_status = 502


# ---------------------------------------------------------------------------
# Seam dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntentExecutionOutcome:
    """Return value of ``IntentExecutor.execute``.

    ``lines_changed`` is optional — some artifact types don't have a natural
    line count (e.g. pure field updates on an issue). Frontend renders only
    when present.
    """

    applied_version: int
    lines_changed: int | None = None


@dataclass(frozen=True)
class ProposalApplyResult:
    """Return value of ``ProposalBus.accept_proposal``."""

    proposal: Proposal
    applied_version: int
    lines_changed: int | None


# ---------------------------------------------------------------------------
# Seam protocols — replaced in later plans
# ---------------------------------------------------------------------------


class SSEPublisherProtocol(Protocol):
    """Protocol the real ``ChatStreamPublisher`` (Plan 02) satisfies."""

    async def publish_proposal_request(self, p: Proposal) -> None: ...
    async def publish_proposal_applied(
        self, p: Proposal, lines_changed: int | None
    ) -> None: ...
    async def publish_proposal_rejected(
        self, p: Proposal, reason: str | None
    ) -> None: ...
    async def publish_proposal_retried(
        self, p: Proposal, hint: str | None
    ) -> None: ...


class IntentExecutorProtocol(Protocol):
    """Protocol the real ``IntentExecutor`` (Plan 03) satisfies."""

    async def execute(
        self,
        *,
        intent_tool: str,
        intent_args: dict[str, Any],
        workspace_id: UUID,
        target_artifact_type: ArtifactType,
        target_artifact_id: UUID,
    ) -> IntentExecutionOutcome: ...


class _NullSSEPublisher:
    """No-op publisher. Replaced by ``ChatStreamPublisher`` in Plan 02."""

    async def publish_proposal_request(self, p: Proposal) -> None:
        return None

    async def publish_proposal_applied(
        self,
        p: Proposal,
        lines_changed: int | None,
    ) -> None:
        return None

    async def publish_proposal_rejected(
        self,
        p: Proposal,
        reason: str | None,
    ) -> None:
        return None

    async def publish_proposal_retried(
        self,
        p: Proposal,
        hint: str | None,
    ) -> None:
        return None


class _NullIntentExecutor:
    """Placeholder executor. Real implementation lands in Plan 03."""

    async def execute(
        self,
        *,
        intent_tool: str,
        intent_args: dict[str, Any],
        workspace_id: UUID,
        target_artifact_type: ArtifactType,
        target_artifact_id: UUID,
    ) -> IntentExecutionOutcome:
        msg = (
            "IntentExecutor not yet wired (Plan 03). "
            f"Refusing to execute tool={intent_tool!r}."
        )
        raise NotImplementedError(msg)


# ---------------------------------------------------------------------------
# ProposalBus
# ---------------------------------------------------------------------------


class ProposalBus:
    """Orchestrates proposal lifecycle: create -> publish -> accept/reject/retry.

    Construction deps: a ``ProposalRepository`` (request-scoped), an SSE
    publisher (Plan 02 wires real one), and an intent executor (Plan 03 wires
    real one). Defaults are no-op / raising stubs so this class is safely
    constructible today.
    """

    def __init__(
        self,
        repository: ProposalRepository,
        sse_publisher: SSEPublisherProtocol | None = None,
        intent_executor: IntentExecutorProtocol | None = None,
    ) -> None:
        self._repo = repository
        self._sse: SSEPublisherProtocol = sse_publisher or _NullSSEPublisher()
        self._executor: IntentExecutorProtocol = intent_executor or _NullIntentExecutor()

    # ----------------------------- create ----------------------------------

    async def create_proposal(
        self,
        *,
        workspace_id: UUID,
        session_id: UUID,
        message_id: UUID,
        target_artifact_type: ArtifactType,
        target_artifact_id: UUID,
        intent_tool: str,
        intent_args: dict[str, Any],
        diff_kind: DiffKind,
        diff_payload: dict[str, Any],
        reasoning: str | None = None,
        mode: ChatMode,
        accept_disabled: bool = False,
        persist: bool = True,
        plan_preview_only: bool = False,
    ) -> Proposal:
        """Persist a PENDING proposal and publish a request SSE event."""
        proposal = await self._repo.create(
            workspace_id=workspace_id,
            session_id=session_id,
            message_id=message_id,
            target_artifact_type=target_artifact_type,
            target_artifact_id=target_artifact_id,
            intent_tool=intent_tool,
            intent_args=intent_args,
            diff_kind=diff_kind,
            diff_payload=diff_payload,
            reasoning=reasoning,
            mode=mode,
            accept_disabled=accept_disabled,
            persist=persist,
            plan_preview_only=plan_preview_only,
        )
        await self._sse.publish_proposal_request(proposal)
        return proposal

    # ----------------------------- accept ----------------------------------

    async def accept_proposal(
        self, proposal_id: UUID, *, decided_by: UUID
    ) -> ProposalApplyResult:
        """Execute the queued intent and mark the proposal APPLIED (or ERRORED)."""
        pending = await self._load_pending(proposal_id)

        try:
            outcome = await self._executor.execute(
                intent_tool=pending.intent_tool,
                intent_args=pending.intent_args,
                workspace_id=pending.workspace_id,
                target_artifact_type=pending.target_artifact_type,
                target_artifact_id=pending.target_artifact_id,
            )
        except Exception as exc:
            await self._repo.update_status(
                pending.id,
                status=ProposalStatus.ERRORED,
                decided_by=decided_by,
                decided_at=datetime.now(UTC),
                applied_version=None,
            )
            # Do NOT publish "applied" — the proposal is ERRORED, not APPLIED.
            # Plan 02 will add an explicit proposal_errored SSE event if the
            # frontend needs to render an error pill.
            raise ProposalIntentExecutionError(
                f"Intent execution failed for proposal {pending.id}: {exc}"
            ) from exc

        applied = await self._repo.update_status(
            pending.id,
            status=ProposalStatus.APPLIED,
            decided_by=decided_by,
            decided_at=datetime.now(UTC),
            applied_version=outcome.applied_version,
        )
        await self._sse.publish_proposal_applied(applied, outcome.lines_changed)
        return ProposalApplyResult(
            proposal=applied,
            applied_version=outcome.applied_version,
            lines_changed=outcome.lines_changed,
        )

    # ----------------------------- reject ----------------------------------

    async def reject_proposal(
        self, proposal_id: UUID, *, decided_by: UUID, reason: str | None = None
    ) -> Proposal:
        pending = await self._load_pending(proposal_id)
        rejected = await self._repo.update_status(
            pending.id,
            status=ProposalStatus.REJECTED,
            decided_by=decided_by,
            decided_at=datetime.now(UTC),
        )
        await self._sse.publish_proposal_rejected(rejected, reason)
        return rejected

    # ----------------------------- retry -----------------------------------

    async def retry_proposal(
        self, proposal_id: UUID, *, decided_by: UUID, hint: str | None = None
    ) -> Proposal:
        pending = await self._load_pending(proposal_id)
        retried = await self._repo.update_status(
            pending.id,
            status=ProposalStatus.RETRIED,
            decided_by=decided_by,
            decided_at=datetime.now(UTC),
        )
        await self._sse.publish_proposal_retried(retried, hint)
        return retried

    # ----------------------------- helpers ---------------------------------

    async def _load_pending(self, proposal_id: UUID) -> Proposal:
        """Fetch a PENDING proposal; raise typed errors on missing/decided."""
        proposal = await self._repo.get_by_id(proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(f"Proposal {proposal_id} not found")
        if proposal.status is not ProposalStatus.PENDING:
            raise ProposalAlreadyDecidedError(
                f"Proposal {proposal_id} already decided (status={proposal.status.value})"
            )
        return proposal


__all__ = [
    "IntentExecutionOutcome",
    "IntentExecutorProtocol",
    "ProposalAlreadyDecidedError",
    "ProposalApplyResult",
    "ProposalBus",
    "ProposalIntentExecutionError",
    "ProposalNotFoundError",
    "SSEPublisherProtocol",
]
