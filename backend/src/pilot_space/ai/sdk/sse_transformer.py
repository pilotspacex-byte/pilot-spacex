"""SSE (Server-Sent Events) transformer for Claude SDK streaming.

Transforms Claude SDK streaming events into PilotSpace SSE format for
real-time AI responses in the frontend.

Reference: DD-058 (SSE for AI Streaming)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from anthropic.types import Message, MessageDeltaEvent, MessageStartEvent


@dataclass(frozen=True, slots=True)
class SSEEvent:
    """Server-Sent Event for AI streaming.

    Attributes:
        event: Event type identifier.
        data: Event payload as JSON-serializable dict.
    """

    event: str
    data: dict[str, Any]

    def to_sse_string(self) -> str:
        """Convert to SSE format string.

        Returns:
            SSE-formatted string with event type and JSON data.
        """
        return f"event: {self.event}\ndata: {json.dumps(self.data)}\n\n"


class SSETransformer:
    """Transformer for Claude SDK events to PilotSpace SSE format.

    Event Types:
        - message_start: Start of AI message
        - text_delta: Incremental text chunk
        - tool_use: Tool call request
        - tool_result: Tool execution result
        - task_progress: Task progress update
        - approval_request: User approval needed
        - message_stop: End of AI message
        - error: Error during processing
    """

    @staticmethod
    def message_start(message: MessageStartEvent | Message) -> SSEEvent:
        """Transform message start event.

        Args:
            message: Claude SDK message start event or message object.

        Returns:
            SSEEvent for message_start.
        """
        # Extract message object
        msg_obj = message.message if isinstance(message, MessageStartEvent) else message

        return SSEEvent(
            event="message_start",
            data={
                "id": msg_obj.id,
                "model": msg_obj.model,
                "role": msg_obj.role,
            },
        )

    @staticmethod
    def text_delta(delta: MessageDeltaEvent | str, index: int = 0) -> SSEEvent:
        """Transform text delta event.

        Args:
            delta: Claude SDK delta event or text string.
            index: Content block index.

        Returns:
            SSEEvent for text_delta.
        """
        # Extract text from delta
        text = getattr(delta.delta, "text", "") if isinstance(delta, MessageDeltaEvent) else delta

        return SSEEvent(
            event="text_delta",
            data={
                "index": index,
                "text": text,
            },
        )

    @staticmethod
    def tool_use(
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str,
    ) -> SSEEvent:
        """Transform tool use event.

        Args:
            tool_name: Name of tool being called.
            tool_input: Tool input parameters.
            tool_use_id: Unique tool use ID.

        Returns:
            SSEEvent for tool_use.
        """
        return SSEEvent(
            event="tool_use",
            data={
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_use_id": tool_use_id,
            },
        )

    @staticmethod
    def tool_result(
        tool_use_id: str,
        result: dict[str, Any] | str,
        is_error: bool = False,
    ) -> SSEEvent:
        """Transform tool result event.

        Args:
            tool_use_id: Tool use ID matching the request.
            result: Tool execution result.
            is_error: Whether result is an error.

        Returns:
            SSEEvent for tool_result.
        """
        return SSEEvent(
            event="tool_result",
            data={
                "tool_use_id": tool_use_id,
                "result": result,
                "is_error": is_error,
            },
        )

    @staticmethod
    def task_progress(
        task_name: str,
        progress: float,
        status: Literal["pending", "running", "completed", "failed"],
        message: str | None = None,
        task_id: str | None = None,
        current_step: str | None = None,
        total_steps: int | None = None,
    ) -> SSEEvent:
        """Transform task progress event.

        Enhanced for T073 with task_id and step tracking.

        Args:
            task_name: Name of the task.
            progress: Progress percentage (0.0-1.0).
            status: Current task status.
            message: Optional status message.
            task_id: Optional task UUID for progress tracking.
            current_step: Optional current step description.
            total_steps: Optional total steps count.

        Returns:
            SSEEvent for task_progress.
        """
        data: dict[str, Any] = {
            "task_name": task_name,
            "progress": progress,
            "status": status,
            "message": message,
        }

        if task_id:
            data["task_id"] = task_id
        if current_step:
            data["current_step"] = current_step
        if total_steps:
            data["total_steps"] = total_steps

        return SSEEvent(
            event="task_progress",
            data=data,
        )

    @staticmethod
    def approval_request(
        approval_id: str,
        action_name: str,
        description: str,
        proposed_changes: dict[str, Any],
    ) -> SSEEvent:
        """Transform approval request event.

        Args:
            approval_id: Unique approval request ID.
            action_name: Name of action requiring approval.
            description: Human-readable description.
            proposed_changes: Proposed changes to approve.

        Returns:
            SSEEvent for approval_request.
        """
        return SSEEvent(
            event="approval_request",
            data={
                "approval_id": approval_id,
                "action_name": action_name,
                "description": description,
                "proposed_changes": proposed_changes,
            },
        )

    @staticmethod
    def message_stop(
        stop_reason: str | None = None,
        usage: dict[str, int] | None = None,
    ) -> SSEEvent:
        """Transform message stop event.

        Args:
            stop_reason: Reason for stopping (end_turn, max_tokens, etc.).
            usage: Token usage stats.

        Returns:
            SSEEvent for message_stop.
        """
        return SSEEvent(
            event="message_stop",
            data={
                "stop_reason": stop_reason,
                "usage": usage or {},
            },
        )

    @staticmethod
    def error(
        error_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> SSEEvent:
        """Transform error event.

        Args:
            error_type: Error type identifier.
            message: Human-readable error message.
            details: Additional error details.

        Returns:
            SSEEvent for error.
        """
        return SSEEvent(
            event="error",
            data={
                "error_type": error_type,
                "message": message,
                "details": details or {},
            },
        )


def transform_claude_event(event: Any) -> SSEEvent | None:
    """Transform Claude SDK event to PilotSpace SSE event.

    Args:
        event: Claude SDK event object.

    Returns:
        SSEEvent if transformable, None if event should be skipped.
    """
    transformer = SSETransformer()

    # Message start
    if isinstance(event, MessageStartEvent):
        return transformer.message_start(event)

    # Text delta
    if isinstance(event, MessageDeltaEvent):
        return transformer.text_delta(event)

    # For other event types, check event type field
    event_type = getattr(event, "type", None)

    if event_type == "content_block_delta":
        # Extract text delta from content block
        delta_obj = getattr(event, "delta", None)
        if delta_obj and hasattr(delta_obj, "text"):
            return transformer.text_delta(delta_obj.text)

    # Skip events that don't need transformation
    return None
