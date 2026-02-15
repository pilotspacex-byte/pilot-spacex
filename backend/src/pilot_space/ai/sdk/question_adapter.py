"""Question adapter for Claude Agent SDK AskUserQuestion events.

Provides:
- QuestionAdapter: Intercepts SDK's AskUserQuestion events and publishes rich SSE events
- Stateless two-turn model: question emits SSE + returns Deny; answer comes as new chat turn
- In-memory registry with cleanup (single-worker v1 assumption)

Reference: specs/014-approval-input-ux/spec.md (T01)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from pilot_space.ai.sdk.sse_transformer import SSEEvent
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

_CLEANUP_STALE_SECONDS = 3600.0  # 1 hour — stale question cleanup


class QuestionOption(BaseModel):
    """Single option in a user question.

    Attributes:
        label: Display text for the option.
        description: Optional helper text for the option.
    """

    label: str
    description: str | None = None


class SkipCondition(BaseModel):
    """Condition to skip a question based on a previous question's answer.

    Attributes:
        questionIndex: 0-based index of the referenced question.
        selectedLabel: If this label is selected in the referenced question, skip this question.
    """

    questionIndex: int = Field(alias="question_index")
    selectedLabel: str = Field(alias="selected_label")

    model_config = {"populate_by_name": True}


class Question(BaseModel):
    """Individual question in AskUserQuestion event.

    Attributes:
        question: The question text to display.
        options: List of selectable options.
        multiSelect: Whether multiple options can be selected.
        header: Optional header/category for the question.
        skipWhen: Conditions to skip this question based on previous answers.
    """

    question: str
    options: list[QuestionOption]
    multiSelect: bool = Field(default=False, alias="multi_select")
    header: str | None = None
    skipWhen: list[SkipCondition] = Field(default_factory=list, alias="skip_when")

    model_config = {"populate_by_name": True}


class QuestionRequestData(BaseModel):
    """SSE event data for question_request.

    Attributes:
        messageId: Message ID from SDK context.
        questionId: Unique ID for this question set (uuid4).
        toolCallId: Tool call ID from SDK context.
        questions: Array of questions to present.
    """

    messageId: str = Field(alias="message_id")
    questionId: str = Field(alias="question_id")
    toolCallId: str = Field(alias="tool_call_id")
    questions: list[Question]

    model_config = {"populate_by_name": True}


class PendingQuestion:
    """Registry entry for a pending question (stateless two-turn model).

    In the two-turn model, the question is registered when emitted and cleaned up
    when the user's answer arrives as a new chat turn via mark_resolved().

    Attributes:
        question_id: Unique identifier for this question.
        tool_call_id: SDK tool call ID.
        questions: The questions presented to user.
        user_id: User who initiated this question (for access control).
        created_at: Timestamp when question was registered (loop time for v1 single-worker).
    """

    __slots__ = (
        "created_at",
        "question_id",
        "questions",
        "tool_call_id",
        "user_id",
    )

    def __init__(
        self,
        question_id: UUID,
        tool_call_id: str,
        questions: list[Question],
        user_id: UUID,
    ):
        self.question_id = question_id
        self.tool_call_id = tool_call_id
        self.questions = questions
        self.user_id = user_id
        # Capture loop time for expiry calculations in single-worker v1
        try:
            loop = asyncio.get_running_loop()
            self.created_at = loop.time()
        except RuntimeError:
            # Fallback if called outside event loop (shouldn't happen in production)
            import time

            self.created_at = time.monotonic()


_MAX_QUESTIONS = 4
_MAX_HEADER_LEN = 12


def _normalize_option(raw: Any) -> dict[str, Any]:
    """Normalize a single option to {label, description} object."""
    if isinstance(raw, str):
        return {"label": raw, "description": None}
    if isinstance(raw, dict):
        label = raw.get("label", raw.get("text", str(raw)))
        description = raw.get("description") or None
        return {"label": str(label), "description": str(description) if description else None}
    return {"label": str(raw), "description": None}


def _normalize_question(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single question dict to match Question schema.

    Handles AI-generated payloads that may use wrong field names,
    string options, missing headers, or extra fields.
    Auto-appends an "Other" free-text option if not already present.
    """
    # Accept both "question" and "text" field names, also "label"
    question_text = raw.get("question") or raw.get("text") or raw.get("label") or ""

    # Normalize options: strings → objects
    raw_options = raw.get("options", [])
    options = (
        [_normalize_option(opt) for opt in raw_options] if isinstance(raw_options, list) else []
    )

    # Auto-append "Other" free-text option if not already present
    has_other = any(opt.get("label", "").strip().lower().startswith("other") for opt in options)
    if not has_other and options:
        options.append({"label": "Other", "description": "Provide your own answer"})

    # Generate header from question text if missing
    header = raw.get("header")
    if not header and question_text:
        header = question_text[:_MAX_HEADER_LEN].rstrip()

    multi_select = raw.get("multiSelect", raw.get("multi_select", False))

    # Pass through skipWhen conditions
    skip_when = raw.get("skipWhen", raw.get("skip_when", []))

    return {
        "question": str(question_text),
        "options": options,
        "multiSelect": bool(multi_select),
        "header": header,
        "skipWhen": skip_when if isinstance(skip_when, list) else [],
    }


def normalize_questions(raw_questions: list[Any]) -> list[dict[str, Any]]:
    """Normalize raw SDK questions to match Question schema.

    Handles: wrong field names, string options, missing headers,
    extra fields, and >4 question overflow.
    """
    result: list[dict[str, Any]] = []
    for item in raw_questions[:_MAX_QUESTIONS]:
        if isinstance(item, dict):
            result.append(_normalize_question(item))
        else:
            logger.warning("Skipping non-dict question item: %s", type(item))
    return result


class QuestionAdapter:
    """Adapter for SDK AskUserQuestion events with rich SSE publishing.

    Responsibilities:
    - Intercept AskUserQuestion from SDK
    - Generate questionId (uuid4)
    - Publish question_request SSE event with structured data
    - Maintain in-memory registry: questionId -> PendingQuestion
    - Mark resolved via mark_resolved() when answer arrives as new chat turn
    - Cleanup answered/expired questions (no memory leak)

    Single-worker v1 assumption: In-memory registry is acceptable (lost on restart).
    Locks are defensive only for v1 single-worker context.

    Usage:
        adapter = get_question_adapter()

        # In SDK transform chain (SYNC context)
        question_id, sse_event = adapter.register_question(
            message_id=msg_id,
            tool_call_id=tool_call_id,
            questions=[...],
            user_id=user_id
        )

        # Later, when user answers (ASYNC context)
        resolved = await adapter.mark_resolved(question_id, user_id)
    """

    def __init__(self) -> None:
        """Initialize adapter with empty registry."""
        self._pending_questions: dict[UUID, PendingQuestion] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[None] | None = None

    def register_question(
        self,
        message_id: str,
        tool_call_id: str,
        questions: list[dict[str, Any]],
        user_id: UUID,
    ) -> tuple[UUID, str]:
        """Register AskUserQuestion in adapter and build SSE event (SYNC).

        This method is SYNC and lock-free for v1 single-worker context.
        Called from the SYNC message transform chain in pilotspace_agent_helpers.py.

        Args:
            message_id: SDK message ID for context.
            tool_call_id: SDK tool call ID.
            questions: Raw question data from SDK.
            user_id: User who initiated this question (for access control).

        Returns:
            Tuple of (question_id, sse_event_string) for publishing.
        """
        question_id = uuid4()

        # Normalize raw SDK output before validation
        normalized = normalize_questions(questions)

        # Validate and convert questions to Pydantic models
        try:
            validated_questions = [Question.model_validate(q) for q in normalized]
        except Exception:
            logger.exception("Failed to validate questions from SDK")
            # Return error event instead of crashing
            error_event = SSEEvent(
                event="error",
                data={
                    "code": "question_validation_error",
                    "message": "Invalid question format from SDK",
                    "recoverable": False,
                },
            )
            return question_id, error_event.to_sse_string()

        # Register in pending questions (no lock needed for v1 single-worker)
        pending = PendingQuestion(
            question_id=question_id,
            tool_call_id=tool_call_id,
            questions=validated_questions,
            user_id=user_id,
        )

        self._pending_questions[question_id] = pending

        logger.info(
            "Registered question: questionId=%s toolCallId=%s questionCount=%d",
            question_id,
            tool_call_id,
            len(validated_questions),
        )

        # Build SSE event
        event_data = QuestionRequestData(
            message_id=message_id,
            question_id=str(question_id),
            tool_call_id=tool_call_id,
            questions=validated_questions,
        )

        sse_event = SSEEvent(
            event="question_request",
            data=event_data.model_dump(),
        )

        return question_id, sse_event.to_sse_string()

    async def mark_resolved(
        self,
        question_id: UUID,
        user_id: UUID,
    ) -> PendingQuestion | None:
        """Mark a pending question as resolved (cleanup from registry).

        Called when the user's answer arrives as a new chat turn.
        The answer content is in the chat message itself, not stored here.

        Args:
            question_id: Unique ID of the question to resolve.
            user_id: User attempting to resolve (must match question owner).

        Returns:
            PendingQuestion if found and valid, None if not found/already resolved/user mismatch.
        """
        async with self._lock:
            # Atomic pop: remove first, validate after, restore on mismatch
            pending = self._pending_questions.pop(question_id, None)

            if pending is None:
                logger.warning(
                    "mark_resolved called for unknown or already-resolved questionId=%s",
                    question_id,
                )
                return None

            # Verify user_id matches; restore if mismatch
            if pending.user_id != user_id:
                self._pending_questions[question_id] = pending
                logger.warning(
                    "mark_resolved called by wrong user: questionId=%s, expected_user=%s, actual_user=%s",
                    question_id,
                    pending.user_id,
                    user_id,
                )
                return None

        logger.info(
            "Marked question resolved: questionId=%s toolCallId=%s",
            question_id,
            pending.tool_call_id,
        )
        return pending

    def get_question(self, question_id: UUID) -> PendingQuestion | None:
        """Get a pending question by ID without removing it (non-destructive peek).

        Used by session finalization to attach question_data to the assistant
        message before persistence, without affecting the answer flow.

        Args:
            question_id: Question UUID to look up.

        Returns:
            PendingQuestion if found and still pending, None otherwise.
        """
        return self._pending_questions.get(question_id)

    async def cleanup_expired(self, timeout_seconds: float = _CLEANUP_STALE_SECONDS) -> int:
        """Clean up questions that have been pending longer than timeout.

        Args:
            timeout_seconds: Max age in seconds before question is expired (default 1 hour).

        Returns:
            Number of expired questions removed.
        """
        try:
            loop = asyncio.get_running_loop()
            now = loop.time()
        except RuntimeError:
            # If called outside event loop, use monotonic time
            import time

            now = time.monotonic()

        expired_ids: list[UUID] = []

        async with self._lock:
            for question_id, pending in self._pending_questions.items():
                age = now - pending.created_at
                if age > timeout_seconds:
                    expired_ids.append(question_id)

            for question_id in expired_ids:
                del self._pending_questions[question_id]

        if expired_ids:
            logger.info(
                "Cleaned up %d expired questions (timeout=%ds)",
                len(expired_ids),
                timeout_seconds,
            )

        return len(expired_ids)

    async def start_cleanup_task(self, interval_seconds: float = 60.0) -> None:
        """Start background cleanup task for expired questions.

        Args:
            interval_seconds: Cleanup interval in seconds (default 60s).
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            logger.warning("Cleanup task already running, skipping start")
            return

        async def cleanup_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    await self.cleanup_expired()
                except asyncio.CancelledError:
                    logger.info("Cleanup task cancelled")
                    break
                except Exception:
                    logger.exception("Error in cleanup task")

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Started question cleanup task (interval=%ds)", interval_seconds)

    async def stop_cleanup_task(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            import contextlib

            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            logger.info("Stopped question cleanup task")

    def get_pending_count(self) -> int:
        """Get count of currently pending questions.

        Returns:
            Number of questions awaiting answers.
        """
        return len(self._pending_questions)

    async def get_pending_sse_events(self) -> list[str]:
        """Get SSE event strings for all pending questions (session recovery).

        When a session is resumed and questions are still pending,
        the frontend needs to re-display them. This method generates
        the same question_request SSE events for recovery.

        Returns:
            List of SSE event strings for each pending question.
        """
        events: list[str] = []
        async with self._lock:
            for pending in self._pending_questions.values():
                sse_string = build_question_sse_event(
                    message_id="recovery",
                    question_id=pending.question_id,
                    tool_call_id=pending.tool_call_id,
                    questions=pending.questions,
                )
                events.append(sse_string)
        return events

    async def get_question_status(self, question_id: UUID) -> dict[str, Any] | None:
        """Get status of a pending question.

        Args:
            question_id: Question ID to check.

        Returns:
            Dict with question metadata if found, None if not pending.
        """
        async with self._lock:
            pending = self._pending_questions.get(question_id)

        if pending is None:
            return None

        loop = asyncio.get_running_loop()
        age = loop.time() - pending.created_at

        return {
            "question_id": str(question_id),
            "tool_call_id": pending.tool_call_id,
            "question_count": len(pending.questions),
            "age_seconds": age,
        }


# ---------------------------------------------------------------------------
# Helper functions for SSE event construction (used by SDK integration)
# ---------------------------------------------------------------------------


def build_question_sse_event(
    message_id: str,
    question_id: UUID,
    tool_call_id: str,
    questions: list[Question],
) -> str:
    """Build SSE event string for question_request.

    Args:
        message_id: SDK message ID.
        question_id: Unique question ID.
        tool_call_id: SDK tool call ID.
        questions: List of Question models.

    Returns:
        SSE-formatted event string.
    """
    event_data = QuestionRequestData(
        message_id=message_id,
        question_id=str(question_id),
        tool_call_id=tool_call_id,
        questions=questions,
    )

    data: dict[str, Any] = event_data.model_dump()
    return f"event: question_request\ndata: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Module-level singleton for single-worker v1 architecture
# ---------------------------------------------------------------------------

_default_adapter: QuestionAdapter | None = None


def get_question_adapter() -> QuestionAdapter:
    """Get or create the module-level singleton QuestionAdapter.

    Returns:
        Singleton QuestionAdapter instance.
    """
    global _default_adapter  # noqa: PLW0603
    if _default_adapter is None:
        _default_adapter = QuestionAdapter()
    return _default_adapter


# ---------------------------------------------------------------------------
# can_use_tool callback factory for Claude Agent SDK integration
# ---------------------------------------------------------------------------


def create_can_use_tool_callback(
    tool_event_queue: asyncio.Queue[str],
    user_id: UUID,
) -> Any:
    """Create a can_use_tool callback (safety net for AskUserQuestion).

    The primary question flow now uses the ask_user MCP tool in interaction_server.py.
    This callback remains as a safety net: if Claude somehow still tries the built-in
    AskUserQuestion tool, it returns PermissionResultDeny with a redirect message.

    For all other tools, returns PermissionResultAllow (pass-through).

    Args:
        tool_event_queue: Queue to push SSE events for the frontend.
        user_id: User who owns this session (for question access control).

    Returns:
        Async callable matching CanUseTool signature.
    """
    from claude_agent_sdk.types import (
        PermissionResultAllow,
        PermissionResultDeny,
        ToolPermissionContext,
    )

    async def can_use_tool(
        tool_name: str,
        tool_input: dict[str, Any],
        context: ToolPermissionContext,
    ) -> PermissionResultAllow | PermissionResultDeny:
        if tool_name != "AskUserQuestion":
            return PermissionResultAllow()

        # Safety net: AskUserQuestion should not be called — ask_user MCP tool
        # handles all user interaction. Log warning and deny.
        logger.warning(
            "AskUserQuestion called unexpectedly (should use ask_user MCP tool). "
            "Returning Deny as safety net."
        )

        return PermissionResultDeny(
            message=(
                "Do not use AskUserQuestion. "
                "Use the ask_user tool instead to present questions to the user."
            ),
        )

    return can_use_tool
