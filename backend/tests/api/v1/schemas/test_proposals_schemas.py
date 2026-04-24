"""Tests for Pydantic schemas in :mod:`pilot_space.api.v1.schemas.proposals`.

Covers:
    * ``ProposalEnvelope.from_entity`` round-trips a Proposal domain entity.
    * ``by_alias`` dumps produce camelCase on the wire.
    * ``ProposalRequestEvent`` is **flat composition** — envelope keys live
      at the top level alongside ``eventTimestamp``, NOT nested.
    * Event validation rejects payloads missing required envelope fields.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from pilot_space.api.v1.schemas.proposals import (
    AcceptProposalRequest,
    ProposalAppliedEvent,
    ProposalEnvelope,
    ProposalListResponse,
    ProposalRejectedEvent,
    ProposalRequestEvent,
    ProposalRetriedEvent,
    RejectProposalRequest,
    RetryProposalRequest,
)
from pilot_space.domain.proposal import (
    ArtifactType,
    ChatMode,
    DiffKind,
    Proposal,
    ProposalStatus,
)


def _sample_proposal(**overrides: object) -> Proposal:
    base: dict[str, object] = {
        "id": uuid4(),
        "workspace_id": uuid4(),
        "session_id": uuid4(),
        "message_id": uuid4(),
        "target_artifact_type": ArtifactType.ISSUE,
        "target_artifact_id": uuid4(),
        "intent_tool": "update_issue",
        "intent_args": {"title": "new title"},
        "diff_kind": DiffKind.FIELDS,
        "diff_payload": {"fields": [{"name": "title", "before": "a", "after": "b"}]},
        "reasoning": "because tests said so",
        "status": ProposalStatus.PENDING,
        "applied_version": None,
        "decided_at": None,
        "decided_by": None,
        "created_at": datetime.now(UTC),
        "mode": ChatMode.ACT,
        "accept_disabled": False,
        "persist": True,
        "plan_preview_only": False,
    }
    base.update(overrides)
    return Proposal(**base)  # type: ignore[arg-type]


class TestProposalEnvelopeFromEntity:
    def test_round_trips_all_fields(self) -> None:
        proposal = _sample_proposal()

        env = ProposalEnvelope.from_entity(proposal)

        assert env.id == proposal.id
        assert env.workspace_id == proposal.workspace_id
        assert env.session_id == proposal.session_id
        assert env.message_id == proposal.message_id
        assert env.target_artifact_type is ArtifactType.ISSUE
        assert env.target_artifact_id == proposal.target_artifact_id
        assert env.intent_tool == "update_issue"
        assert env.intent_args == {"title": "new title"}
        assert env.diff_kind is DiffKind.FIELDS
        assert env.diff_payload == proposal.diff_payload
        assert env.reasoning == "because tests said so"
        assert env.status is ProposalStatus.PENDING
        assert env.mode is ChatMode.ACT
        assert env.accept_disabled is False
        assert env.persist is True
        assert env.plan_preview_only is False

    def test_dump_by_alias_produces_camel_case(self) -> None:
        proposal = _sample_proposal()
        env = ProposalEnvelope.from_entity(proposal)

        dumped = env.model_dump(by_alias=True)

        assert "workspaceId" in dumped
        assert "sessionId" in dumped
        assert "messageId" in dumped
        assert "targetArtifactType" in dumped
        assert "intentTool" in dumped
        assert "diffKind" in dumped
        assert "acceptDisabled" in dumped
        assert "planPreviewOnly" in dumped
        # snake_case field names should NOT appear in the aliased dump
        assert "workspace_id" not in dumped
        assert "plan_preview_only" not in dumped


class TestProposalRequestEventFlatComposition:
    def test_flat_shape_no_envelope_nesting(self) -> None:
        """Envelope keys MUST live at the top level alongside eventTimestamp."""
        proposal = _sample_proposal()
        envelope_fields = ProposalEnvelope.from_entity(proposal).model_dump()
        now = datetime.now(UTC)

        event = ProposalRequestEvent(**envelope_fields, eventTimestamp=now)
        dumped = event.model_dump(by_alias=True, mode="json")

        # Envelope keys at the top level.
        assert dumped["id"] == str(proposal.id)
        assert dumped["intentTool"] == "update_issue"
        assert dumped["workspaceId"] == str(proposal.workspace_id)
        # Event-only key.
        assert "eventTimestamp" in dumped
        # Critically: NO nested 'envelope' key.
        assert "envelope" not in dumped

    def test_rejects_payload_missing_id(self) -> None:
        proposal = _sample_proposal()
        envelope_fields = ProposalEnvelope.from_entity(proposal).model_dump()
        envelope_fields.pop("id")

        with pytest.raises(ValidationError):
            ProposalRequestEvent(**envelope_fields, eventTimestamp=datetime.now(UTC))

    def test_rejects_payload_missing_intent_tool(self) -> None:
        proposal = _sample_proposal()
        envelope_fields = ProposalEnvelope.from_entity(proposal).model_dump()
        envelope_fields.pop("intent_tool")

        with pytest.raises(ValidationError):
            ProposalRequestEvent(**envelope_fields, eventTimestamp=datetime.now(UTC))

    def test_model_validate_accepts_camel_case_input(self) -> None:
        proposal = _sample_proposal()
        envelope_fields = ProposalEnvelope.from_entity(proposal).model_dump(by_alias=True)

        event = ProposalRequestEvent.model_validate(
            {**envelope_fields, "eventTimestamp": datetime.now(UTC).isoformat()}
        )

        assert event.id == proposal.id


class TestSiblingEvents:
    def test_applied_event_round_trip(self) -> None:
        pid = uuid4()
        event = ProposalAppliedEvent(
            proposalId=pid,
            appliedVersion=7,
            linesChanged=42,
            timestamp=datetime.now(UTC),
        )

        dumped = event.model_dump(by_alias=True)

        assert dumped["proposalId"] == pid
        assert dumped["appliedVersion"] == 7
        assert dumped["linesChanged"] == 42

    def test_applied_event_lines_changed_optional(self) -> None:
        event = ProposalAppliedEvent(
            proposalId=uuid4(), appliedVersion=1, timestamp=datetime.now(UTC)
        )
        assert event.lines_changed is None

    def test_rejected_event_round_trip(self) -> None:
        pid = uuid4()
        event = ProposalRejectedEvent(
            proposalId=pid,
            reason="out of scope",
            timestamp=datetime.now(UTC),
        )
        dumped = event.model_dump(by_alias=True)
        assert dumped["proposalId"] == pid
        assert dumped["reason"] == "out of scope"

    def test_retried_event_round_trip(self) -> None:
        pid = uuid4()
        event = ProposalRetriedEvent(
            proposalId=pid,
            hint="smaller scope",
            timestamp=datetime.now(UTC),
        )
        dumped = event.model_dump(by_alias=True)
        assert dumped["proposalId"] == pid
        assert dumped["hint"] == "smaller scope"


class TestRequestBodies:
    def test_accept_request_is_empty(self) -> None:
        body = AcceptProposalRequest()
        assert body.model_dump() == {}

    def test_reject_request_accepts_reason(self) -> None:
        body = RejectProposalRequest(reason="nope")
        assert body.reason == "nope"

    def test_reject_request_rejects_overlong_reason(self) -> None:
        with pytest.raises(ValidationError):
            RejectProposalRequest(reason="x" * 2001)

    def test_retry_request_accepts_hint(self) -> None:
        body = RetryProposalRequest(hint="make it smaller")
        assert body.hint == "make it smaller"


class TestProposalListResponse:
    def test_empty_default(self) -> None:
        resp = ProposalListResponse()
        assert resp.proposals == []
        assert resp.pending_count == 0

    def test_serialises_nested_envelopes(self) -> None:
        proposal = _sample_proposal()
        env = ProposalEnvelope.from_entity(proposal)
        resp = ProposalListResponse(proposals=[env], pendingCount=1)

        dumped = resp.model_dump(by_alias=True)

        assert dumped["pendingCount"] == 1
        assert len(dumped["proposals"]) == 1
        assert dumped["proposals"][0]["intentTool"] == "update_issue"


class TestRequestEventInstanceOfEnvelope:
    """ProposalRequestEvent MUST be a subclass of ProposalEnvelope.

    Plan 04 frontend casts ``event.data as ProposalEnvelope`` — this only
    works when the event is truly a superset (inheritance, not composition).
    """

    def test_inheritance_chain(self) -> None:
        assert issubclass(ProposalRequestEvent, ProposalEnvelope)

    def test_instance_check(self) -> None:
        proposal = _sample_proposal()
        envelope_fields = ProposalEnvelope.from_entity(proposal).model_dump()
        event = ProposalRequestEvent(
            **envelope_fields, eventTimestamp=datetime.now(UTC)
        )
        assert isinstance(event, ProposalEnvelope)


# Silence unused-import warnings for auxiliary fixtures kept for readability.
_ = UUID
