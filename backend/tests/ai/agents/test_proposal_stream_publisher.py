"""Tests for :class:`ProposalStreamPublisher` (Phase 89 Plan 02).

Verifies that every ``publish_*`` method:

1. Resolves the queue via the injected ``get_queue_for_session`` callable.
2. Builds a wire-format SSE frame whose ``event:`` line matches the
   corresponding :class:`StreamEvent` value.
3. Puts exactly one frame onto the queue.
4. Degrades gracefully — if no queue is registered for the session, the
   publish is a no-op (no exception).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.agents.pilotspace_stream_utils import StreamEvent
from pilot_space.ai.agents.proposal_stream_publisher import ProposalStreamPublisher
from pilot_space.domain.proposal import (
    ArtifactType,
    ChatMode,
    DiffKind,
    Proposal,
    ProposalStatus,
)


def _make_proposal(**overrides: object) -> Proposal:
    base: dict[str, object] = {
        "id": uuid4(),
        "workspace_id": uuid4(),
        "session_id": uuid4(),
        "message_id": uuid4(),
        "target_artifact_type": ArtifactType.ISSUE,
        "target_artifact_id": uuid4(),
        "intent_tool": "update_issue",
        "intent_args": {"title": "new"},
        "diff_kind": DiffKind.FIELDS,
        "diff_payload": {"fields": []},
        "reasoning": "reason",
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


def _parse_frame(frame: str) -> tuple[str, dict[str, object]]:
    """Split a ``event: NAME\\ndata: JSON\\n\\n`` frame into (name, data)."""
    lines = [line for line in frame.split("\n") if line]
    event_line = next(line for line in lines if line.startswith("event: "))
    data_line = next(line for line in lines if line.startswith("data: "))
    return event_line[len("event: ") :], json.loads(data_line[len("data: ") :])


class TestPublisherRequestEvent:
    @pytest.mark.asyncio
    async def test_publish_proposal_request_enqueues_exactly_one_frame(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = ProposalStreamPublisher(get_queue_for_session=lambda _sid: queue)
        proposal = _make_proposal()

        await publisher.publish_proposal_request(proposal)

        assert queue.qsize() == 1
        frame = queue.get_nowait()
        name, data = _parse_frame(frame)
        assert name == StreamEvent.PROPOSAL_REQUEST.value
        assert data["id"] == str(proposal.id)
        assert data["intentTool"] == "update_issue"
        assert data["workspaceId"] == str(proposal.workspace_id)
        assert "eventTimestamp" in data
        # Flat composition — envelope NOT nested.
        assert "envelope" not in data

    @pytest.mark.asyncio
    async def test_publish_proposal_request_resolves_queue_by_session_id(self) -> None:
        """Publisher MUST call the resolver with the proposal's session id."""
        captured: list[UUID] = []
        queue: asyncio.Queue[str] = asyncio.Queue()

        def resolver(session_id: UUID) -> asyncio.Queue[str]:
            captured.append(session_id)
            return queue

        publisher = ProposalStreamPublisher(get_queue_for_session=resolver)
        proposal = _make_proposal()

        await publisher.publish_proposal_request(proposal)

        assert captured == [proposal.session_id]


class TestPublisherAppliedEvent:
    @pytest.mark.asyncio
    async def test_publish_proposal_applied_frame(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = ProposalStreamPublisher(get_queue_for_session=lambda _sid: queue)
        proposal = _make_proposal(
            status=ProposalStatus.APPLIED,
            applied_version=5,
        )

        await publisher.publish_proposal_applied(proposal, lines_changed=12)

        assert queue.qsize() == 1
        name, data = _parse_frame(queue.get_nowait())
        assert name == StreamEvent.PROPOSAL_APPLIED.value
        assert data["proposalId"] == str(proposal.id)
        assert data["appliedVersion"] == 5
        assert data["linesChanged"] == 12

    @pytest.mark.asyncio
    async def test_publish_proposal_applied_lines_changed_may_be_null(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = ProposalStreamPublisher(get_queue_for_session=lambda _sid: queue)
        proposal = _make_proposal(
            status=ProposalStatus.APPLIED, applied_version=3
        )

        await publisher.publish_proposal_applied(proposal, lines_changed=None)

        _, data = _parse_frame(queue.get_nowait())
        assert data["linesChanged"] is None


class TestPublisherRejectedEvent:
    @pytest.mark.asyncio
    async def test_publish_proposal_rejected_with_reason(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = ProposalStreamPublisher(get_queue_for_session=lambda _sid: queue)
        proposal = _make_proposal(status=ProposalStatus.REJECTED)

        await publisher.publish_proposal_rejected(proposal, reason="out of scope")

        name, data = _parse_frame(queue.get_nowait())
        assert name == StreamEvent.PROPOSAL_REJECTED.value
        assert data["proposalId"] == str(proposal.id)
        assert data["reason"] == "out of scope"

    @pytest.mark.asyncio
    async def test_publish_proposal_rejected_reason_may_be_null(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = ProposalStreamPublisher(get_queue_for_session=lambda _sid: queue)
        proposal = _make_proposal(status=ProposalStatus.REJECTED)

        await publisher.publish_proposal_rejected(proposal, reason=None)

        _, data = _parse_frame(queue.get_nowait())
        assert data["reason"] is None


class TestPublisherRetriedEvent:
    @pytest.mark.asyncio
    async def test_publish_proposal_retried_with_hint(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = ProposalStreamPublisher(get_queue_for_session=lambda _sid: queue)
        proposal = _make_proposal(status=ProposalStatus.RETRIED)

        await publisher.publish_proposal_retried(proposal, hint="smaller")

        name, data = _parse_frame(queue.get_nowait())
        assert name == StreamEvent.PROPOSAL_RETRIED.value
        assert data["proposalId"] == str(proposal.id)
        assert data["hint"] == "smaller"


class TestPublisherResilience:
    @pytest.mark.asyncio
    async def test_no_registered_queue_is_a_noop(self) -> None:
        """If resolver returns None, publish does nothing (no exception)."""
        publisher = ProposalStreamPublisher(get_queue_for_session=lambda _sid: None)
        proposal = _make_proposal()

        # Must not raise.
        await publisher.publish_proposal_request(proposal)
        await publisher.publish_proposal_applied(
            _make_proposal(status=ProposalStatus.APPLIED, applied_version=1),
            lines_changed=0,
        )
        await publisher.publish_proposal_rejected(proposal, reason=None)
        await publisher.publish_proposal_retried(proposal, hint=None)

    @pytest.mark.asyncio
    async def test_default_resolver_is_noop(self) -> None:
        """Default construction (no resolver) must not raise."""
        publisher = ProposalStreamPublisher()
        await publisher.publish_proposal_request(_make_proposal())

    @pytest.mark.asyncio
    async def test_queue_error_is_swallowed(self) -> None:
        """If put raises, publish logs + continues — the bus must stay alive."""

        class BrokenQueue:
            async def put(self, _frame: str) -> None:
                raise RuntimeError("queue offline")

        publisher = ProposalStreamPublisher(
            get_queue_for_session=lambda _sid: BrokenQueue(),  # type: ignore[arg-type,return-value]
        )
        # Must not raise.
        await publisher.publish_proposal_request(_make_proposal())
