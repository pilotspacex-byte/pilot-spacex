"""In-process SDK custom tool for user interaction (ask_user).

Replaces the SDK's built-in AskUserQuestion (CLI tool) with a custom MCP tool
that returns a normal tool result instead of PermissionResultDeny. This eliminates
leaked text from Claude's response to the Deny message.

Architecture:
  ClaudeSDKClient (in-process) → ask_user tool handler → registers question
  → emits question_request SSE via EventPublisher queue → returns success result
  → Claude sees normal tool_result → ends turn cleanly (no noise text)

Reference: Feature 014 (Approval Input UX)
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.ai.mcp.event_publisher import EventPublisher
from pilot_space.ai.sdk.question_adapter import get_question_adapter, normalize_questions
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

SERVER_NAME = "pilot-interaction"

TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__ask_user",
]


def _text_result(text: str) -> dict[str, Any]:
    """Create a standard MCP tool text result."""
    return {"content": [{"type": "text", "text": text}]}


async def handle_ask_user(
    args: dict[str, Any],
    publisher: EventPublisher,
    user_id: UUID,
) -> dict[str, Any]:
    """Core handler for ask_user tool — testable without MCP server wrapper.

    Args:
        args: Tool arguments from Claude (must contain 'questions' array).
        publisher: EventPublisher for SSE event delivery.
        user_id: User ID for question ownership (access control).

    Returns:
        MCP tool result dict with pending_answer status or error.
    """
    raw_questions = args.get("questions", [])
    if not isinstance(raw_questions, list) or not raw_questions:
        return _text_result("Error: 'questions' must be a non-empty array (max 4 items).")

    adapter = get_question_adapter()

    # Register question (normalizes + validates + creates PendingQuestion)
    question_id, sse_event = adapter.register_question(
        message_id="mcp_ask_user",
        tool_call_id="mcp_ask_user",
        questions=raw_questions,
        user_id=user_id,
    )

    # Emit SSE event to frontend via the EventPublisher queue
    await publisher.publish(sse_event)

    logger.info(
        "[InteractionServer] ask_user: questionId=%s, questionCount=%d",
        question_id,
        len(normalize_questions(raw_questions)),
    )

    return _text_result(
        json.dumps(
            {
                "status": "pending_answer",
                "questionId": str(question_id),
                "message": (
                    "Questions displayed to user. "
                    "Their answer will arrive as the next message. "
                    "Do not add commentary — just end your response."
                ),
            }
        )
    )


def create_interaction_server(
    publisher: EventPublisher,
    *,
    user_id: UUID | None = None,
) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server with the ask_user tool.

    The ask_user tool replaces the SDK's built-in AskUserQuestion. It:
    1. Normalizes and validates questions from Claude's output
    2. Registers the question in QuestionAdapter (generates UUID)
    3. Emits question_request SSE event to the frontend via EventPublisher
    4. Returns a normal tool result telling Claude to wait for the answer

    Args:
        publisher: EventPublisher for SSE event delivery.
        user_id: User ID for question ownership (access control).

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions.mcp_servers.
    """
    if user_id is None:
        raise ValueError("user_id is required for interaction server")

    @tool(
        "ask_user",
        "Present questions to the user and wait for their response. "
        "Use this when you need user input, clarification, or a decision. "
        "The user's answer will arrive as the next message in the conversation. "
        "Do NOT add commentary after calling this tool — just end your response.",
        {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "description": (
                        "Array of questions (max 4). Each question has: "
                        "question (string), header (short label, max 12 chars), "
                        "options (array of {label, description}, 2-4 per question), "
                        "multiSelect (boolean, default false)."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question text to display",
                            },
                            "header": {
                                "type": "string",
                                "description": "Short label (max 12 chars)",
                            },
                            "options": {
                                "type": "array",
                                "description": "2-4 selectable options",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "label": {
                                            "type": "string",
                                            "description": "Option display text",
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Option helper text",
                                        },
                                    },
                                    "required": ["label"],
                                },
                            },
                            "multiSelect": {
                                "type": "boolean",
                                "description": "Allow multiple selections",
                            },
                            "skipWhen": {
                                "type": "array",
                                "description": (
                                    "Conditions to skip this question based on previous answers. "
                                    "Each condition references a prior question by 0-based index."
                                ),
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "questionIndex": {
                                            "type": "integer",
                                            "description": "0-based index of the referenced question",
                                        },
                                        "selectedLabel": {
                                            "type": "string",
                                            "description": "Skip if this label was selected",
                                        },
                                    },
                                    "required": ["questionIndex", "selectedLabel"],
                                },
                            },
                        },
                        "required": ["question", "options"],
                    },
                    "maxItems": 4,
                },
            },
            "required": ["questions"],
        },
    )
    async def ask_user(args: dict[str, Any]) -> dict[str, Any]:
        """Present questions to the user via SSE and return pending status."""
        return await handle_ask_user(args, publisher, user_id)

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[ask_user],
    )
