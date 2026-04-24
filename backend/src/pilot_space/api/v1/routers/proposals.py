"""REST router for the Edit Proposal pipeline (Phase 89 Plan 02).

Routes:

* ``POST /api/v1/proposals/{id}/accept`` — execute the queued intent.
* ``POST /api/v1/proposals/{id}/reject`` — mark proposal REJECTED (optional reason).
* ``POST /api/v1/proposals/{id}/retry``  — mark proposal RETRIED (optional hint).
* ``GET  /api/v1/proposals?session_id=`` — list proposals for a session.

All endpoints are session-scoped via the ``X-Workspace-Id`` header (see
``.claude/rules/di-wiring.md``). The router delegates to
:class:`ProposalBus`; domain exceptions (``ProposalNotFoundError``,
``ProposalAlreadyDecidedError``, ``ProposalIntentExecutionError``) propagate
to the global ``app_error_handler`` which emits RFC 7807 problem+json.

**Revert is out of scope here** — Plan 05 will add
``POST /api/v1/proposals/{id}/revert`` to this same module.
"""

from __future__ import annotations

from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from pilot_space.api.v1.schemas.proposals import (
    ProposalEnvelope,
    ProposalListResponse,
    RejectProposalRequest,
    RetryProposalRequest,
    RevertResultEnvelope,
    VersionHistoryEntry,
)
from pilot_space.application.services.proposal_bus import ProposalBus
from pilot_space.application.services.proposal_repository import ProposalRepository
from pilot_space.container.container import Container
from pilot_space.dependencies.auth import CurrentUserId, SessionDep
from pilot_space.dependencies.workspace import HeaderWorkspaceMemberId
from pilot_space.domain.proposal import ProposalStatus

router = APIRouter(prefix="/proposals", tags=["proposals"])


# ---------------------------------------------------------------------------
# Local DI adapters — kept inside the router module (simpler than shipping
# dedicated ``Dep`` aliases through ``api/v1/dependencies.py`` just for the
# GET list endpoint, which needs the repo directly).
# ---------------------------------------------------------------------------


@inject
def _get_proposal_bus(
    bus: ProposalBus = Depends(Provide[Container.proposal_bus]),
) -> ProposalBus:
    return bus


@inject
def _get_proposal_repository(
    repo: ProposalRepository = Depends(Provide[Container.proposal_repository]),
) -> ProposalRepository:
    return repo


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/{proposal_id}/accept", response_model=ProposalEnvelope)
async def accept_proposal(
    proposal_id: UUID,
    session: SessionDep,
    workspace_id: HeaderWorkspaceMemberId,
    current_user: CurrentUserId,
    bus: ProposalBus = Depends(_get_proposal_bus),
) -> ProposalEnvelope:
    """Accept a pending proposal — execute the intent and flip status to APPLIED."""
    result = await bus.accept_proposal(proposal_id, decided_by=current_user)
    return ProposalEnvelope.from_entity(result.proposal)


@router.post("/{proposal_id}/reject", response_model=ProposalEnvelope)
async def reject_proposal(
    proposal_id: UUID,
    body: RejectProposalRequest,
    session: SessionDep,
    workspace_id: HeaderWorkspaceMemberId,
    current_user: CurrentUserId,
    bus: ProposalBus = Depends(_get_proposal_bus),
) -> ProposalEnvelope:
    """Reject a pending proposal (optional free-text reason)."""
    proposal = await bus.reject_proposal(
        proposal_id, decided_by=current_user, reason=body.reason
    )
    return ProposalEnvelope.from_entity(proposal)


@router.post("/{proposal_id}/retry", response_model=ProposalEnvelope)
async def retry_proposal(
    proposal_id: UUID,
    body: RetryProposalRequest,
    session: SessionDep,
    workspace_id: HeaderWorkspaceMemberId,
    current_user: CurrentUserId,
    bus: ProposalBus = Depends(_get_proposal_bus),
) -> ProposalEnvelope:
    """Mark a proposal as RETRIED so the agent can reissue with a narrower scope."""
    proposal = await bus.retry_proposal(
        proposal_id, decided_by=current_user, hint=body.hint
    )
    return ProposalEnvelope.from_entity(proposal)


@router.post("/{proposal_id}/revert", response_model=RevertResultEnvelope)
async def revert_proposal(
    proposal_id: UUID,
    session: SessionDep,
    workspace_id: HeaderWorkspaceMemberId,
    current_user: CurrentUserId,
    bus: ProposalBus = Depends(_get_proposal_bus),
) -> RevertResultEnvelope:
    """Revert an APPLIED proposal within the 10-minute window (Phase 89 Plan 05).

    Domain exceptions (``ProposalNotFoundError`` 404,
    ``ProposalCannotBeRevertedError`` 409) propagate to the global RFC 7807
    handler. The server clock is the authoritative source of truth for the
    window — frontend mirrors it as a UX hint only.
    """
    result = await bus.revert_proposal(proposal_id, decided_by=current_user)
    return RevertResultEnvelope(
        proposal=ProposalEnvelope.from_entity(result.proposal),
        new_version_number=result.new_version_number,
        new_history_entry=VersionHistoryEntry.model_validate(result.new_history_entry),
    )


@router.get("", response_model=ProposalListResponse)
async def list_proposals(
    session: SessionDep,
    workspace_id: HeaderWorkspaceMemberId,
    session_id: UUID = Query(..., alias="session_id"),
    repo: ProposalRepository = Depends(_get_proposal_repository),
) -> ProposalListResponse:
    """List proposals for a chat session (newest first)."""
    proposals = await repo.list_by_session(session_id)
    envelopes = [ProposalEnvelope.from_entity(p) for p in proposals]
    pending_count = sum(1 for p in proposals if p.status is ProposalStatus.PENDING)
    return ProposalListResponse(proposals=envelopes, pending_count=pending_count)


__all__ = ["router"]
