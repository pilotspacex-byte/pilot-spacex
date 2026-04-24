"""Real SSE publisher for the Edit Proposal pipeline (Phase 89 Plan 02).

Satisfies the :class:`SSEPublisherProtocol` seam left by Plan 01's
:class:`ProposalBus`. The publisher resolves the per-session SSE queue via
an injected callable (``get_queue_for_session``), serialises the proposal
into the Pydantic event payloads defined in
:mod:`pilot_space.api.v1.schemas.proposals`, and wraps the JSON in the
wire-format SSE frame produced by :func:`build_sse_frame`.

Resilience (per ``.claude/rules/ai-layer.md``):

* The publisher wraps the queue put in :func:`asyncio.wait_for` with a 5s
  timeout.
* On timeout / lookup failure / unexpected exception, the publisher logs a
  structured warning and swallows the exception. The SSE consumer (Plan 04)
  can fall back to the REST ``GET /proposals?session_id=`` list endpoint to
  refetch the proposal — dropping a frame is not fatal.
* The queue-registry seam is intentionally permissive: if no registry is
  wired yet (Plan 04 owns per-session queue registration), the publisher is
  a no-op and logs at DEBUG, so Plan 02 can ship today without breaking CI.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.agents.pilotspace_stream_utils import StreamEvent, build_sse_frame
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.domain.proposal import Proposal

logger = get_logger(__name__)

# Seconds to wait for a put() onto a downstream queue before giving up.
_PUT_TIMEOUT_SECONDS = 5.0


# Type alias — resolves the active SSE queue for a session. Returns ``None``
# when no active stream exists for that session (publisher becomes a no-op).
QueueResolver = Callable[[UUID], "asyncio.Queue[str] | None"]


def _no_queue(_session_id: UUID) -> asyncio.Queue[str] | None:
    """Default resolver — always returns ``None`` (publisher is inert).

    Plan 04 will wire the real per-session queue registry. Until then the
    publisher emits nothing, which is correct: nobody is subscribed to the
    stream yet either.
    """
    return None


class ProposalStreamPublisher:
    """Push proposal lifecycle events onto the per-session chat SSE queue.

    Implements :class:`pilot_space.application.services.proposal_bus.SSEPublisherProtocol`.
    """

    def __init__(
        self,
        *,
        get_queue_for_session: QueueResolver | None = None,
    ) -> None:
        self._get_queue = get_queue_for_session or _no_queue

    # ------------------------------------------------------------------ helpers

    async def _put_frame(
        self,
        session_id: UUID,
        event: StreamEvent,
        payload: dict[str, object],
    ) -> None:
        """Resolve the session queue and enqueue an SSE frame with a 5s timeout."""
        queue = self._get_queue(session_id)
        if queue is None:
            logger.debug(
                "proposal_stream_publisher_no_queue",
                session_id=str(session_id),
                event_name=event.value,
            )
            return

        frame = build_sse_frame(event, payload)
        try:
            await asyncio.wait_for(queue.put(frame), timeout=_PUT_TIMEOUT_SECONDS)
        except TimeoutError:
            logger.warning(
                "proposal_stream_publisher_timeout",
                session_id=str(session_id),
                event_name=event.value,
            )
        except Exception as exc:
            logger.warning(
                "proposal_stream_publisher_error",
                session_id=str(session_id),
                event_name=event.value,
                error=str(exc),
            )

    # ------------------------------------------------------------------ API

    async def publish_proposal_request(self, p: Proposal) -> None:
        """Emit ``proposal_request`` with the full envelope (flat-composed).

        Schema modules are imported lazily to avoid a circular import cycle:
        ``container -> proposal_stream_publisher -> api.v1.schemas -> api.v1.__init__ -> routers -> container``.
        """
        from pilot_space.api.v1.schemas.proposals import (
            ProposalEnvelope,
            ProposalRequestEvent,
        )

        envelope_fields = ProposalEnvelope.from_entity(p).model_dump()
        event = ProposalRequestEvent(
            **envelope_fields,
            event_timestamp=datetime.now(UTC),
        )
        await self._put_frame(
            p.session_id,
            StreamEvent.PROPOSAL_REQUEST,
            event.model_dump(by_alias=True, mode="json"),
        )

    async def publish_proposal_applied(
        self, p: Proposal, lines_changed: int | None
    ) -> None:
        """Emit ``proposal_applied`` with the new version + optional line delta."""
        from pilot_space.api.v1.schemas.proposals import ProposalAppliedEvent

        # ``applied_version`` is guaranteed non-None on APPLIED proposals.
        applied_version = p.applied_version if p.applied_version is not None else 0
        event = ProposalAppliedEvent(
            proposal_id=p.id,
            applied_version=applied_version,
            lines_changed=lines_changed,
            timestamp=datetime.now(UTC),
        )
        await self._put_frame(
            p.session_id,
            StreamEvent.PROPOSAL_APPLIED,
            event.model_dump(by_alias=True, mode="json"),
        )

    async def publish_proposal_rejected(
        self, p: Proposal, reason: str | None
    ) -> None:
        """Emit ``proposal_rejected`` with an optional rejection reason."""
        from pilot_space.api.v1.schemas.proposals import ProposalRejectedEvent

        event = ProposalRejectedEvent(
            proposal_id=p.id,
            reason=reason,
            timestamp=datetime.now(UTC),
        )
        await self._put_frame(
            p.session_id,
            StreamEvent.PROPOSAL_REJECTED,
            event.model_dump(by_alias=True, mode="json"),
        )

    async def publish_proposal_retried(self, p: Proposal, hint: str | None) -> None:
        """Emit ``proposal_retried`` with an optional retry hint."""
        from pilot_space.api.v1.schemas.proposals import ProposalRetriedEvent

        event = ProposalRetriedEvent(
            proposal_id=p.id,
            hint=hint,
            timestamp=datetime.now(UTC),
        )
        await self._put_frame(
            p.session_id,
            StreamEvent.PROPOSAL_RETRIED,
            event.model_dump(by_alias=True, mode="json"),
        )

    async def publish_proposal_reverted(
        self,
        p: Proposal,
        *,
        new_version_number: int,
        reverted_from_version: int,
    ) -> None:
        """Emit ``proposal_reverted`` with the new + prior version numbers.

        Phase 89 Plan 05 — distinct from ``proposal_applied`` so frontend
        dispatch can swap AppliedReceipt -> RevertedPill without a flag lookup.
        """
        from pilot_space.api.v1.schemas.proposals import ProposalRevertedEvent

        event = ProposalRevertedEvent(
            proposal_id=p.id,
            new_version_number=new_version_number,
            reverted_from_version=reverted_from_version,
            timestamp=datetime.now(UTC),
        )
        await self._put_frame(
            p.session_id,
            StreamEvent.PROPOSAL_REVERTED,
            event.model_dump(by_alias=True, mode="json"),
        )


__all__ = ["ProposalStreamPublisher", "QueueResolver"]
