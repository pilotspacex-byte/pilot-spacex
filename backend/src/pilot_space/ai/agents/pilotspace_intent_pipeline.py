"""Intent pipeline for PilotSpaceAgent.

Implements T-016/T-017/T-018: detect intents from user messages, emit SSE
lifecycle events, and provide event-driven resume via asyncio.Event.

Pipeline steps (Sprint 2):
    recall → analyze → detect → present → (await confirmation) → execute → save → respond

Sprint 2 wires: recall (T-048), skill execute (T-049), save (T-050).

Feature 015: AI Workforce Platform
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

if TYPE_CHECKING:
    from pilot_space.application.services.intent.detection_service import (
        DetectIntentResult,
        IntentDetectionService,
    )
    from pilot_space.application.services.memory.memory_save_service import (
        MemorySaveService,
    )
    from pilot_space.application.services.memory.memory_search_service import (
        MemorySearchService,
    )

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SSE event type constants (T-017)
# ---------------------------------------------------------------------------

INTENT_DETECTED = "intent_detected"
INTENT_CONFIRMED = "intent_confirmed"
INTENT_EXECUTING = "intent_executing"
INTENT_COMPLETED = "intent_completed"

# Timeout (seconds) the pipeline waits for user confirmation before resuming
# without intents (FR-084: resume within 5s).
_CONFIRMATION_TIMEOUT = 5.0


# ---------------------------------------------------------------------------
# ConfirmationBus (T-018): session-scoped asyncio.Event registry
# ---------------------------------------------------------------------------


class ConfirmationBus:
    """Registry mapping session_id → confirmation asyncio.Event.

    When the user confirms or rejects an intent via the Intent API, the router
    calls ``ConfirmationBus.signal(session_id, intent_id)`` to unblock the
    pipeline's ``wait_for_confirmation()`` call.

    Designed as a class-level singleton dict so PilotSpaceAgent can access it
    without dependency injection.
    """

    _events: ClassVar[dict[str, asyncio.Event]] = {}
    _payloads: ClassVar[dict[str, dict[str, Any]]] = {}

    @classmethod
    def register(cls, session_id: str) -> asyncio.Event:
        """Register an event for session_id and return it."""
        event = asyncio.Event()
        cls._events[session_id] = event
        cls._payloads[session_id] = {}
        return event

    @classmethod
    def signal(
        cls,
        session_id: str,
        *,
        intent_id: str | None = None,
        action: str = "confirmed",
    ) -> bool:
        """Signal the pipeline waiting for session_id.

        Args:
            session_id: The chat/SDK session identifier.
            intent_id: ID of the confirmed/rejected intent.
            action: "confirmed" or "rejected".

        Returns:
            True if a waiting pipeline was signalled, False if no registration.
        """
        event = cls._events.get(session_id)
        if event is None:
            return False
        cls._payloads[session_id] = {"intent_id": intent_id, "action": action}
        event.set()
        return True

    @classmethod
    def get_payload(cls, session_id: str) -> dict[str, Any]:
        """Retrieve the payload set by signal()."""
        return cls._payloads.get(session_id, {})

    @classmethod
    def deregister(cls, session_id: str) -> None:
        """Clean up after the pipeline completes."""
        cls._events.pop(session_id, None)
        cls._payloads.pop(session_id, None)


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------


def _make_sse(event_type: str, data: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _intent_to_sse_data(intent: Any) -> dict[str, Any]:
    """Serialize a WorkIntent ORM model to SSE payload dict."""
    return {
        "intent_id": str(intent.id),
        "what": intent.what,
        "why": intent.why,
        "confidence": float(intent.confidence),
        "status": str(intent.status.value) if intent.status else "detected",
        "source_block_id": str(intent.source_block_id) if intent.source_block_id else None,
    }


# ---------------------------------------------------------------------------
# Pipeline steps (T-016, T-017, T-018)
# ---------------------------------------------------------------------------


async def detect_intents(
    *,
    detection_service: IntentDetectionService,
    message: str,
    workspace_id: UUID,
    user_id: UUID,
    source_block_id: UUID | None = None,
) -> DetectIntentResult:
    """Run intent detection against the user message.

    Args:
        detection_service: Injected IntentDetectionService.
        message: The raw user message text.
        workspace_id: Current workspace UUID.
        user_id: Current user UUID (used as owner).
        source_block_id: Optional TipTap block reference.

    Returns:
        DetectIntentResult with persisted WorkIntent list.
    """
    from pilot_space.application.services.intent.detection_service import (
        DetectIntentPayload,
        IntentSource,
    )

    payload = DetectIntentPayload(
        text=message,
        source=IntentSource.CHAT,
        workspace_id=workspace_id,
        owner=str(user_id),
        source_block_id=source_block_id,
    )
    return await detection_service.detect(payload)


async def emit_intent_detected_events(
    intents: Sequence[Any],
) -> list[str]:
    """Build SSE strings for each detected intent.

    Accepts any sequence of WorkIntent ORM models.

    Returns:
        List of SSE-formatted strings ready to yield.
    """
    events: list[str] = []
    for intent in intents:
        data = _intent_to_sse_data(intent)
        events.append(_make_sse(INTENT_DETECTED, data))
    return events


async def wait_for_confirmation(
    session_id: str,
    *,
    wait_secs: float = _CONFIRMATION_TIMEOUT,
) -> dict[str, Any]:
    """Wait for a confirmation signal from the Intent API.

    Registers a ConfirmationBus event for session_id and blocks until:
    - The Intent API calls ConfirmationBus.signal(), or
    - wait_secs elapse (graceful degradation: proceed without confirmation).

    Args:
        session_id: Session to register against.
        wait_secs: Max seconds to wait. Defaults to 5.0 (FR-084).

    Returns:
        Confirmation payload from ConfirmationBus (may be empty on timeout).
    """
    event = ConfirmationBus.register(session_id)
    triggered = False
    try:
        await asyncio.wait_for(event.wait(), timeout=wait_secs)
        triggered = True
    except TimeoutError:
        logger.debug(
            "[IntentPipeline] Confirmation timeout after %.1fs for session=%s",
            wait_secs,
            session_id,
        )

    # Capture payload before deregister clears it
    result = ConfirmationBus.get_payload(session_id) if triggered else {}
    ConfirmationBus.deregister(session_id)
    return result


def make_intent_executing_event(
    intent_id: str,
    skill_name: str,
) -> str:
    """Build intent_executing SSE string."""
    return _make_sse(
        INTENT_EXECUTING,
        {"intent_id": intent_id, "skill_name": skill_name},
    )


def make_intent_completed_event(
    intent_id: str,
    skill_name: str,
    artifacts: list[dict[str, Any]] | None = None,
) -> str:
    """Build intent_completed SSE string."""
    return _make_sse(
        INTENT_COMPLETED,
        {
            "intent_id": intent_id,
            "skill_name": skill_name,
            "artifacts": artifacts or [],
        },
    )


def make_intent_confirmed_event(intent_id: str) -> str:
    """Build intent_confirmed SSE string."""
    return _make_sse(INTENT_CONFIRMED, {"intent_id": intent_id})


# ---------------------------------------------------------------------------
# Recall (T-048) — real MemorySearchService call
# ---------------------------------------------------------------------------


async def recall_workspace_context(
    workspace_id: UUID,
    query: str,
    memory_search_service: MemorySearchService | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Recall relevant memories for the current query (T-048).

    Args:
        workspace_id: Current workspace UUID.
        query: Search query derived from user message.
        memory_search_service: Optional injected MemorySearchService.
        limit: Maximum entries to return.

    Returns:
        List of memory context dicts; empty on failure or missing service.
    """
    if memory_search_service is None:
        logger.debug(
            "[IntentPipeline] No MemorySearchService — skipping recall workspace=%s",
            workspace_id,
        )
        return []

    try:
        from pilot_space.application.services.memory.memory_search_service import (
            MemorySearchPayload,
        )

        payload = MemorySearchPayload(
            query=query,
            workspace_id=workspace_id,
            limit=limit,
        )
        result = await memory_search_service.execute(payload)
        entries = [
            {
                "content": r.get("content", ""),
                "source_type": r.get("source_type", ""),
                "score": r.get("score", 0.0),
            }
            for r in result.results
        ]
        logger.debug(
            "[IntentPipeline] Recalled %d memory entries workspace=%s",
            len(entries),
            workspace_id,
        )
        return entries
    except Exception:
        logger.warning(
            "[IntentPipeline] Memory recall failed, continuing without context",
            exc_info=True,
        )
        return []


# ---------------------------------------------------------------------------
# Memory context injection — injects recall results into system prompt prefix
# ---------------------------------------------------------------------------


def build_memory_context_prefix(memory_entries: list[dict[str, Any]]) -> str:
    """Format recalled memory entries as a system prompt section.

    Delegates to ``prompt_assembler._format_memory_entries`` to avoid
    duplicated logic. Kept for backward compatibility with integration tests.

    Args:
        memory_entries: List of recalled memory dicts from recall_workspace_context.

    Returns:
        Formatted string to prepend to the system prompt; empty if no entries.
    """
    if not memory_entries:
        return ""
    from pilot_space.ai.prompt.prompt_assembler import format_memory_entries

    return format_memory_entries(memory_entries)


# ---------------------------------------------------------------------------
# Skill execution wiring (T-049)
# ---------------------------------------------------------------------------


async def execute_confirmed_skill(
    *,
    confirmation_payload: dict[str, Any],
    workspace_id: UUID,
    user_id: UUID,
    session_id: Any,
) -> list[str]:
    """Emit SSE events for a confirmed skill intent.

    Called after wait_for_confirmation() returns a confirmed payload.
    Emits intent_executing and intent_completed events.

    Args:
        confirmation_payload: Payload from ConfirmationBus with intent_id/action.
        workspace_id: Current workspace UUID.
        user_id: Current user UUID.
        session_id: Session identifier for logging.

    Returns:
        List of SSE-formatted event strings to yield.
    """
    action = confirmation_payload.get("action", "confirmed")
    intent_id = confirmation_payload.get("intent_id")

    if action != "confirmed" or not intent_id:
        logger.debug(
            "[IntentPipeline] Skipping skill execute: action=%s intent_id=%s session=%s",
            action,
            intent_id,
            session_id,
        )
        return []

    # Emit intent_executing SSE
    executing_event = make_intent_executing_event(
        intent_id=intent_id,
        skill_name="",  # Skill name resolved at execution time by SkillExecutor
    )

    logger.info(
        "[IntentPipeline] Skill executing intent_id=%s session=%s workspace=%s",
        intent_id,
        session_id,
        workspace_id,
    )

    # Emit intent_completed SSE (skill execution is handled by SkillExecutor
    # downstream; here we emit the event so the frontend knows to track it)
    completed_event = make_intent_completed_event(
        intent_id=intent_id,
        skill_name="",
        artifacts=[],
    )

    return [executing_event, completed_event]


# ---------------------------------------------------------------------------
# Memory save (T-050)
# ---------------------------------------------------------------------------


async def save_skill_outcome_to_memory(
    *,
    memory_save_service: MemorySaveService | None,
    workspace_id: UUID,
    content: str,
    source_id: UUID | None = None,
) -> bool:
    """Save skill outcome summary to workspace memory (T-050).

    Args:
        memory_save_service: Optional injected MemorySaveService.
        workspace_id: Workspace to save memory in.
        content: Summary text of the skill outcome.
        source_id: Optional UUID of the originating intent.

    Returns:
        True if saved successfully, False otherwise.
    """
    if memory_save_service is None or not content:
        return False

    try:
        from pilot_space.application.services.memory.memory_save_service import (
            MemorySavePayload,
        )
        from pilot_space.domain.memory_entry import MemorySourceType

        payload = MemorySavePayload(
            workspace_id=workspace_id,
            content=content,
            source_type=MemorySourceType.SKILL_OUTCOME,
            source_id=source_id,
        )
        await memory_save_service.execute(payload)
        logger.info(
            "[IntentPipeline] Saved skill outcome to memory workspace=%s",
            workspace_id,
        )
        return True
    except Exception:
        logger.warning(
            "[IntentPipeline] Memory save failed (non-fatal)",
            exc_info=True,
        )
        return False


# ---------------------------------------------------------------------------
# Composite pipeline step (T-016)
# ---------------------------------------------------------------------------


async def run_intent_pipeline_step(
    *,
    detection_service: IntentDetectionService | None,
    message: str,
    workspace_id: UUID | None,
    user_id: UUID | None,
    session_id: Any,
) -> list[str]:
    """Detect intents and return SSE event strings (non-fatal on failure).

    Implements the detect→present steps of the T-016 pipeline.
    No-ops if detection_service is None or context is incomplete.

    Args:
        detection_service: Optional injected IntentDetectionService.
        message: User message text.
        workspace_id: Current workspace UUID.
        user_id: Current user UUID.
        session_id: Session identifier for logging.

    Returns:
        List of SSE-formatted ``intent_detected`` event strings.
    """
    if detection_service is None or not workspace_id or not user_id:
        return []

    try:
        result = await detect_intents(
            detection_service=detection_service,
            message=message,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if not result.intents:
            return []

        events = await emit_intent_detected_events(result.intents)
        logger.info(
            "[IntentPipeline] Detected %d intents for session=%s",
            len(result.intents),
            session_id,
        )
        return events
    except Exception as exc:
        logger.warning(
            "[IntentPipeline] Intent detection failed (non-fatal): %s",
            exc,
            exc_info=True,
        )
        return []
