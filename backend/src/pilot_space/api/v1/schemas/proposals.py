"""Pydantic schemas for the Edit Proposal pipeline (Phase 89 Plan 02).

These schemas define both the REST request/response bodies for
``/api/v1/proposals/*`` and the SSE event payloads pushed onto the chat
stream by :class:`ProposalStreamPublisher`.

Wire shape contract (FROZEN — consumed by Plans 04-06 and the frontend):

* :class:`ProposalEnvelope` mirrors the :class:`Proposal` domain entity
  one-to-one. Camel-case on the wire (via ``BaseSchema``'s alias generator).
* :class:`ProposalRequestEvent` uses **flat composition** — it inherits from
  :class:`ProposalEnvelope` and adds ``event_timestamp``. After
  ``model_dump(by_alias=True)`` the resulting dict has envelope keys at the
  top level alongside ``eventTimestamp`` (NOT a nested ``envelope`` key).
  This is what lets Plan 04 frontend cast ``event.data as ProposalEnvelope``
  directly.
* :class:`ProposalAppliedEvent` / :class:`ProposalRejectedEvent` /
  :class:`ProposalRetriedEvent` are lean siblings: just the proposal id plus
  state-specific fields (applied version + lines changed, reason, hint).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema
from pilot_space.domain.proposal import (
    ArtifactType,
    ChatMode,
    DiffKind,
    Proposal,
    ProposalStatus,
)

# ---------------------------------------------------------------------------
# Canonical envelope — mirrors the Proposal domain entity.
# ---------------------------------------------------------------------------


class ProposalEnvelope(BaseSchema):
    """Full proposal envelope — every field the frontend needs to render a card."""

    id: UUID
    workspace_id: UUID
    session_id: UUID
    message_id: UUID
    target_artifact_type: ArtifactType
    target_artifact_id: UUID
    intent_tool: str
    intent_args: dict[str, Any] = Field(default_factory=dict)
    diff_kind: DiffKind
    diff_payload: dict[str, Any] = Field(default_factory=dict)
    reasoning: str | None = None
    status: ProposalStatus
    applied_version: int | None = None
    decided_at: datetime | None = None
    decided_by: UUID | None = None
    created_at: datetime
    # REV-89-01-A / REV-89-02-A: policy flags.
    mode: ChatMode
    accept_disabled: bool = False
    persist: bool = True
    plan_preview_only: bool = False

    @classmethod
    def from_entity(cls, proposal: Proposal) -> ProposalEnvelope:
        """Build an envelope from a :class:`Proposal` domain entity.

        Subclass-safe: returns ``cls(...)`` so :class:`ProposalRequestEvent`
        can override and add ``event_timestamp`` without copy-pasting
        construction logic.
        """
        return cls(
            id=proposal.id,
            workspace_id=proposal.workspace_id,
            session_id=proposal.session_id,
            message_id=proposal.message_id,
            target_artifact_type=proposal.target_artifact_type,
            target_artifact_id=proposal.target_artifact_id,
            intent_tool=proposal.intent_tool,
            intent_args=proposal.intent_args,
            diff_kind=proposal.diff_kind,
            diff_payload=proposal.diff_payload,
            reasoning=proposal.reasoning,
            status=proposal.status,
            applied_version=proposal.applied_version,
            decided_at=proposal.decided_at,
            decided_by=proposal.decided_by,
            created_at=proposal.created_at,
            mode=proposal.mode,
            accept_disabled=proposal.accept_disabled,
            persist=proposal.persist,
            plan_preview_only=proposal.plan_preview_only,
        )


# ---------------------------------------------------------------------------
# SSE event payloads.
# ---------------------------------------------------------------------------


class ProposalRequestEvent(ProposalEnvelope):
    """SSE payload for ``proposal_request``.

    Flat composition: the dump has envelope keys at the top level plus
    ``eventTimestamp``. Plan 04 frontend casts ``event.data as ProposalEnvelope``
    — this only works because we did NOT nest the envelope under a key.
    """

    event_timestamp: datetime


class ProposalAppliedEvent(BaseSchema):
    """SSE payload for ``proposal_applied``."""

    proposal_id: UUID
    applied_version: int
    lines_changed: int | None = None
    timestamp: datetime


class ProposalRejectedEvent(BaseSchema):
    """SSE payload for ``proposal_rejected``."""

    proposal_id: UUID
    reason: str | None = None
    timestamp: datetime


class ProposalRetriedEvent(BaseSchema):
    """SSE payload for ``proposal_retried``."""

    proposal_id: UUID
    hint: str | None = None
    timestamp: datetime


# ---------------------------------------------------------------------------
# REST request bodies.
# ---------------------------------------------------------------------------


class AcceptProposalRequest(BaseSchema):
    """Body for ``POST /proposals/{id}/accept`` — empty today.

    Kept as an explicit schema so future policy knobs (e.g. "apply only if
    current version still matches") can be added without changing the route
    signature.
    """


class RejectProposalRequest(BaseSchema):
    """Body for ``POST /proposals/{id}/reject``."""

    reason: str | None = Field(default=None, max_length=2000)


class RetryProposalRequest(BaseSchema):
    """Body for ``POST /proposals/{id}/retry``."""

    hint: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------------------
# REST responses.
# ---------------------------------------------------------------------------


class ProposalListResponse(BaseSchema):
    """Response for ``GET /proposals?session_id=``."""

    proposals: list[ProposalEnvelope] = Field(default_factory=list)
    pending_count: int = 0


__all__ = [
    "AcceptProposalRequest",
    "ProposalAppliedEvent",
    "ProposalEnvelope",
    "ProposalListResponse",
    "ProposalRejectedEvent",
    "ProposalRequestEvent",
    "ProposalRetriedEvent",
    "RejectProposalRequest",
    "RetryProposalRequest",
]
