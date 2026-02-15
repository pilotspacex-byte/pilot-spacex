"""Helper functions for PilotSpace Agent.

SSE event emission, message transformation, and subagent definitions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from claude_agent_sdk import AgentDefinition

from pilot_space.ai.agents.pilotspace_note_helpers import (
    emit_append_blocks_event,
    emit_insert_blocks_event,
    emit_issue_creation_events,
    emit_remove_block_event,
    emit_remove_content_event,
    emit_replace_block_event,
    emit_replace_content_event,
    extract_citation,
    transform_todo_to_task_progress,
    transform_user_message_tool_results,
    validate_structured_output,
)
from pilot_space.ai.agents.stream_event_transformer import transform_stream_event
from pilot_space.ai.mcp.comment_server import TOOL_NAMES as COMMENT_TOOL_NAMES
from pilot_space.ai.mcp.interaction_server import TOOL_NAMES as INTERACTION_TOOL_NAMES
from pilot_space.ai.mcp.issue_relation_server import TOOL_NAMES as ISSUE_REL_TOOL_NAMES
from pilot_space.ai.mcp.issue_server import TOOL_NAMES as ISSUE_TOOL_NAMES
from pilot_space.ai.mcp.note_content_server import TOOL_NAMES as NOTE_CONTENT_TOOL_NAMES
from pilot_space.ai.mcp.note_server import TOOL_NAMES as NOTE_TOOL_NAMES
from pilot_space.ai.mcp.project_server import TOOL_NAMES as PROJECT_TOOL_NAMES
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from claude_agent_sdk import Message

    from pilot_space.ai.agents.pilotspace_agent import ChatInput
    from pilot_space.ai.agents.sse_delta_buffer import DeltaBuffer

logger = get_logger(__name__)

# Aggregated tool names across all MCP servers (33 tools total: 27 spec + 6 retained)
ALL_TOOL_NAMES: list[str] = [
    *NOTE_TOOL_NAMES,
    *NOTE_CONTENT_TOOL_NAMES,
    *ISSUE_TOOL_NAMES,
    *ISSUE_REL_TOOL_NAMES,
    *PROJECT_TOOL_NAMES,
    *COMMENT_TOOL_NAMES,
    *INTERACTION_TOOL_NAMES,
]


def has_skill_files(skills_dir: Path) -> bool:
    """Check if any SKILL.md files exist under skills_dir subdirectories."""
    if not skills_dir.is_dir():
        return False
    return any((entry / "SKILL.md").is_file() for entry in skills_dir.iterdir() if entry.is_dir())


def build_subagent_definitions() -> dict[str, AgentDefinition]:
    """Build subagent definitions for SDK agent spawning.
    Each subagent has a dedicated model, tool set, and detailed prompt aligned with provider routing per DD-011.
    """
    return {
        "pr-review": AgentDefinition(
            description="Expert code reviewer for GitHub PRs",
            prompt=(
                "You are a senior code reviewer specializing in architecture, security, "
                "and performance analysis. Review the pull request thoroughly:\n"
                "1. Identify security vulnerabilities (OWASP Top 10)\n"
                "2. Check architecture compliance with project patterns\n"
                "3. Evaluate performance implications\n"
                "4. Assess test coverage adequacy\n"
                "Tag each finding with severity: CRITICAL, HIGH, MEDIUM, LOW, INFO."
            ),
            tools=["Read", "Glob", "Grep", "WebFetch", "Bash"],
            model="opus",
        ),
        "ai-context": AgentDefinition(
            description="Aggregates context for issues from notes, code, and tasks",
            prompt=(
                "You are a context aggregation specialist. For the given issue, "
                "find and organize all relevant context:\n"
                "1. Related notes and meeting documents\n"
                "2. Relevant code files and functions\n"
                "3. Similar or duplicate issues\n"
                "4. Dependency relationships\n"
                "Return a structured summary with references."
            ),
            tools=["Read", "Glob", "Grep"],
            model="opus",
        ),
        "doc-generator": AgentDefinition(
            description="Generates technical documentation from code and architecture",
            prompt=(
                "You are a technical writer. Generate clear, comprehensive documentation:\n"
                "1. Follow existing project documentation style\n"
                "2. Include code examples where appropriate\n"
                "3. Document public APIs with parameters and return types\n"
                "4. Add architecture decision references (DD-XXX) where relevant."
            ),
            tools=["Read", "Glob", "Grep", "Write"],
            model="sonnet",
        ),
    }


def build_contextual_message(
    input_data: ChatInput,
    *,
    block_ref_map: Any | None = None,
) -> str:
    """Enrich user message with note/issue context for the SDK.

    When ``block_ref_map`` is provided, block references use human-readable
    ¶N notation instead of raw UUIDs. The model is instructed to use ¶N
    references when calling note tools.

    Args:
        input_data: Chat input with message and context.
        block_ref_map: Optional BlockRefMap for ¶N block references.
    """
    parts: list[str] = []

    note = input_data.context.get("note")
    note_id = input_data.context.get("note_id")
    if note is not None:
        note_title = getattr(note, "title", "Untitled") or "Untitled"
        note_content = getattr(note, "content", {})

        note_header = f"# {note_title}"
        if note_id:
            note_header += f"\nnote_id: {note_id}"

        selected_block_ids = input_data.context.get("selected_block_ids", [])
        if selected_block_ids and block_ref_map is not None:
            refs = [block_ref_map.to_ref(str(bid)) for bid in selected_block_ids]
            note_header += f"\nselected_blocks: {', '.join(refs)}"
        elif selected_block_ids:
            note_header += (
                f"\nselected_block_ids: {', '.join(str(bid) for bid in selected_block_ids)}"
            )

        if block_ref_map is not None and not block_ref_map.is_empty:
            note_header += (
                "\n\nBlocks are identified by ¶N references (e.g., ¶1, ¶2). "
                'Use ¶N when calling note tools (e.g., block_id="¶3"). '
                "Never expose raw block UUIDs to the user."
            )

        if note_content:
            from pilot_space.application.services.note.content_converter import (
                ContentConverter,
            )

            converter = ContentConverter()
            markdown = converter.tiptap_to_markdown(
                note_content,
                block_ref_map=block_ref_map,
            )
            if markdown.strip():
                parts.append(f"<note_context>\n{note_header}\n\n{markdown}\n</note_context>")
        else:
            parts.append(f"<note_context>\n{note_header}\n\n(empty note)\n</note_context>")

    selected_text = input_data.context.get("selected_text")
    if selected_text:
        parts.append(f"<selected_text>\n{selected_text}\n</selected_text>")

    if parts:
        context_block = "\n\n".join(parts)
        return f"{context_block}\n\n{input_data.message}"
    return input_data.message


def transform_sdk_message(  # noqa: PLR0911
    message: Message,
    current_message_id_holder: dict[str, Any],
    delta_buffer: DeltaBuffer | None = None,
    app_session_id: str | None = None,
    user_id: UUID | None = None,
) -> str | None:
    """Transform Claude SDK message to frontend SSE event.

    Converts SDK message types (SystemMessage, AssistantMessage, ResultMessage,
    ToolResultMessage) to ``event: <type>\\ndata: <json>\\n\\n`` SSE format
    with camelCase field names. Note tool results emit content_update events.

    Args:
        message: SDK message object.
        current_message_id_holder: Dict to track current message ID across calls.
        delta_buffer: Optional buffer for water pumping (SSE event reduction).
        app_session_id: Application session ID (UUID) for session tracking.
        user_id: User ID for question registration (enables [ANSWER:] resolution).
    """
    msg_type = type(message).__name__

    if msg_type == "StreamEvent":
        event_data = getattr(message, "event", {})
        parent_tool_use_id = getattr(message, "parent_tool_use_id", None)
        return transform_stream_event(
            event_data,
            parent_tool_use_id,
            current_message_id_holder,
            delta_buffer,
        )

    # Handle SDK ToolResultMessage (legacy compat) and ToolResult
    if msg_type in ("ToolResultMessage", "ToolResult"):
        raw_tool_input = getattr(message, "input", None) or getattr(message, "tool_input", None)
        return transform_tool_result(
            message,
            tool_input=raw_tool_input if isinstance(raw_tool_input, dict) else None,
        )

    # Handle UserMessage with ToolResultBlock content (current SDK)
    # The Claude Agent SDK emits tool results as UserMessage objects
    # containing ToolResultBlock entries, not as standalone ToolResultMessage.
    if msg_type == "UserMessage":
        return transform_user_message_tool_results(message)

    if msg_type == "SystemMessage":
        raw_data = getattr(message, "data", None)
        if isinstance(raw_data, dict) and raw_data.get("type") == "system":
            subtype = raw_data.get("subtype")
            if subtype == "init":
                sdk_session_id = raw_data.get("session_id", "")
                current_message_id_holder["_current_message_id"] = str(uuid4())
                # Reset stale dedup state from previous request (prevents session leak)
                current_message_id_holder.pop("_stream_events_sent", None)
                current_message_id_holder.pop("_streamed_block_indices", None)
                # Use application session_id (UUID) if provided, else fall back to SDK's
                effective_session_id = app_session_id or sdk_session_id
                data: dict[str, Any] = {
                    "messageId": current_message_id_holder["_current_message_id"],
                    "sessionId": str(effective_session_id),
                }
                model = raw_data.get("model")
                if model:
                    data["model"] = str(model)
                return f"event: message_start\ndata: {json.dumps(data)}\n\n"
            # T57: Memory update events from cross-session memory tool
            if subtype == "memory":
                message_id = current_message_id_holder.get("_current_message_id") or ""
                memory_data: dict[str, Any] = {
                    "messageId": message_id,
                    "operation": raw_data.get("operation", "write"),
                    "key": raw_data.get("key", ""),
                    "value": raw_data.get("value"),
                }
                return f"event: memory_update\ndata: {json.dumps(memory_data)}\n\n"
        return None

    if msg_type == "AssistantMessage":
        content = getattr(message, "content", None)
        if content is None:
            return None

        message_id_value = current_message_id_holder.get("_current_message_id")
        message_id = message_id_value if message_id_value else str(uuid4())

        # Dedup: check if stream events already forwarded these blocks
        # Use get() instead of pop() to preserve dedup state across multiple
        # partial AssistantMessages when include_partial_messages=True
        stream_events_sent = bool(current_message_id_holder.get("_stream_events_sent", False))
        raw_indices = current_message_id_holder.get("_streamed_block_indices")
        streamed_indices: set[int] = raw_indices if isinstance(raw_indices, set) else set()

        if isinstance(content, list):
            events: list[str] = []
            text_parts: list[str] = []
            # G-07: Track thinking blocks individually for interleaved rendering
            thinking_blocks: list[dict[str, Any]] = []
            thinking_signature: str | None = None
            citation_parts: list[dict[str, Any]] = []

            for block_idx, block in enumerate(content):
                # Skip blocks already forwarded via StreamEvent
                if stream_events_sent and block_idx in streamed_indices:
                    continue
                block_type = _get_block_type(block)

                # Emit content_block_start for each block (G-01: include thinking type)
                if block_type == "tool_use":
                    content_type = "tool_use"
                elif block_type in ("thinking", "redacted_thinking"):
                    content_type = "thinking"
                else:
                    content_type = "text"
                block_start_data: dict[str, Any] = {
                    "index": block_idx,
                    "contentType": content_type,
                }

                # Include parentToolUseId for subagent content correlation (G12)
                parent_id = None
                if isinstance(block, dict):
                    parent_id = block.get("parent_tool_use_id")
                else:
                    parent_id = getattr(block, "parent_tool_use_id", None)
                if parent_id:
                    block_start_data["parentToolUseId"] = str(parent_id)

                events.append(
                    f"event: content_block_start\ndata: {json.dumps(block_start_data)}\n\n",
                )

                if block_type == "thinking":
                    thinking_text = _get_block_text(block, "thinking")
                    if thinking_text:
                        # G-07: Track each thinking block with its position index
                        thinking_blocks.append(
                            {
                                "content": thinking_text,
                                "blockIndex": block_idx,
                            }
                        )
                    # G-06: Capture signature for multi-turn thinking integrity
                    sig = (
                        block.get("signature")
                        if isinstance(block, dict)
                        else getattr(block, "signature", None)
                    )
                    if sig:
                        thinking_signature = str(sig)
                elif block_type == "redacted_thinking":
                    # G-04: Handle redacted thinking from Claude safety system
                    thinking_blocks.append(
                        {
                            "content": "[Thinking redacted by safety system]",
                            "blockIndex": block_idx,
                            "redacted": True,
                        }
                    )
                elif block_type == "tool_use":
                    tool_event = _handle_tool_use_block(block, message_id, user_id)
                    if tool_event:
                        events.append(tool_event)
                elif block_type == "server_tool_use":
                    # G-10: Handle server-side tool invocations (web_search, etc.)
                    tool_event = _handle_server_tool_use_block(block)
                    if tool_event:
                        events.append(tool_event)
                elif block_type == "web_search_tool_result":
                    # G-10: Handle web search results from server tools
                    search_event = _handle_web_search_result_block(block)
                    if search_event:
                        events.append(search_event)
                elif block_type == "citation":
                    # T58: Extract citation blocks for source attribution
                    citation_data = extract_citation(block)
                    if citation_data:
                        citation_parts.append(citation_data)
                else:
                    text = _get_block_text(block, "text")
                    if text:
                        text_parts.append(text)
                    # G-05: Extract inline citations from TextBlock.citations array
                    inline_citations = (
                        block.get("citations", [])
                        if isinstance(block, dict)
                        else getattr(block, "citations", [])
                    )
                    if inline_citations:
                        for cite in inline_citations:
                            citation_data = extract_citation(cite)
                            if citation_data:
                                citation_parts.append(citation_data)

            # G-07: Emit per-block thinking_delta events for interleaved rendering
            for tb in thinking_blocks:
                thinking_data: dict[str, Any] = {
                    "messageId": message_id,
                    "delta": tb["content"],
                    "blockIndex": tb["blockIndex"],
                }
                if tb.get("redacted"):
                    thinking_data["redacted"] = True
                # G-06: Include signature on the last thinking block
                if thinking_signature and tb is thinking_blocks[-1]:
                    thinking_data["signature"] = thinking_signature
                events.append(
                    f"event: thinking_delta\ndata: {json.dumps(thinking_data)}\n\n",
                )

            if text_parts:
                text_content = " ".join(text_parts)
                text_data = {
                    "messageId": message_id,
                    "delta": text_content,
                }
                events.append(
                    f"event: text_delta\ndata: {json.dumps(text_data)}\n\n",
                )

            # T58: Emit citation events for source attribution
            if citation_parts:
                citation_event_data: dict[str, Any] = {
                    "messageId": message_id,
                    "citations": citation_parts,
                }
                events.append(
                    f"event: citation\ndata: {json.dumps(citation_event_data)}\n\n",
                )

            return "".join(events) if events else None

        text_content = str(content)
        if not text_content.strip():
            return None
        data = {
            "messageId": message_id,
            "delta": text_content,
        }
        return f"event: text_delta\ndata: {json.dumps(data)}\n\n"

    if msg_type == "ResultMessage":
        _session_id = getattr(message, "session_id", "")  # Reserved for future use
        is_error = getattr(message, "is_error", False)
        usage = getattr(message, "usage", None)
        message_id_value = current_message_id_holder.get("_current_message_id")
        message_id = message_id_value if message_id_value else str(uuid4())

        if is_error:
            result = getattr(message, "result", "")
            error_data: dict[str, Any] = {
                "errorCode": "api_error",
                "message": str(result) if result else "Unknown error",
                "retryable": False,
            }
            return f"event: error\ndata: {json.dumps(error_data)}\n\n"

        # Check for structured output in result (G-03: validate before emission)
        events_prefix = ""
        result_raw = getattr(message, "result", None)
        if isinstance(result_raw, dict) and "schemaType" in result_raw:
            schema_type = result_raw["schemaType"]
            validated = validate_structured_output(schema_type, result_raw)
            if validated is not None:
                structured_data: dict[str, Any] = {
                    "messageId": message_id,
                    "schemaType": schema_type,
                    "data": validated,
                }
                events_prefix = f"event: structured_result\ndata: {json.dumps(structured_data)}\n\n"

        data_stop: dict[str, Any] = {
            "messageId": message_id,
            "stopReason": "end_turn",
        }
        if usage:
            input_tokens = getattr(usage, "input_tokens", 0)
            output_tokens = getattr(usage, "output_tokens", 0)
            cached_read = getattr(usage, "cached_read_input_tokens", 0)
            cached_creation = getattr(
                usage,
                "cached_creation_input_tokens",
                0,
            )
            data_stop["usage"] = {
                "inputTokens": input_tokens,
                "outputTokens": output_tokens,
                "totalTokens": input_tokens + output_tokens,
                "cachedTokens": cached_read + cached_creation,
                "cachedReadTokens": cached_read,
                "cachedCreationTokens": cached_creation,
            }
            total_cost = getattr(usage, "total_cost_usd", None)
            if total_cost is not None:
                data_stop["costUsd"] = total_cost
        stop_event = f"event: message_stop\ndata: {json.dumps(data_stop)}\n\n"
        return f"{events_prefix}{stop_event}" if events_prefix else stop_event

    return None


def _handle_tool_use_block(block: Any, message_id: str, user_id: UUID | None = None) -> str | None:
    """Handle tool_use block: emit tool_use SSE event.

    Args:
        block: Tool use block from SDK.
        message_id: Current message ID.
        user_id: User ID (reserved for future use).

    Returns:
        SSE event string or None.
    """
    if isinstance(block, dict):
        tool_name = block.get("name", "")
        tool_input = block.get("input", {})
        tool_id = block.get("id", str(uuid4()))
    else:
        tool_name = getattr(block, "name", "")
        tool_input = getattr(block, "input", {})
        tool_id = getattr(block, "id", str(uuid4()))

    if not tool_name:
        return None

    # Standard tool_use event
    tool_data: dict[str, Any] = {
        "toolCallId": str(tool_id),
        "toolName": tool_name,
        "toolInput": tool_input,
    }
    return f"event: tool_use\ndata: {json.dumps(tool_data)}\n\n"


def _handle_server_tool_use_block(block: Any) -> str | None:
    """Handle server_tool_use block (G-10): map to standard tool_use event."""
    if isinstance(block, dict):
        tool_name = block.get("name", "server_tool")
        tool_id = block.get("id", block.get("server_tool_use_id", str(uuid4())))
        tool_input = block.get("input", {})
    else:
        tool_name = getattr(block, "name", "server_tool")
        tool_id = getattr(block, "id", getattr(block, "server_tool_use_id", str(uuid4())))
        tool_input = getattr(block, "input", {})

    tool_data: dict[str, Any] = {
        "toolCallId": str(tool_id),
        "toolName": tool_name,
        "toolInput": tool_input if isinstance(tool_input, dict) else {},
    }
    return f"event: tool_use\ndata: {json.dumps(tool_data)}\n\n"


def _handle_web_search_result_block(block: Any) -> str | None:
    """Handle web_search_tool_result block (G-10): emit tool_result with search results."""
    if isinstance(block, dict):
        tool_id = block.get("tool_use_id", str(uuid4()))
        search_results = block.get("content", [])
    else:
        tool_id = getattr(block, "tool_use_id", str(uuid4()))
        search_results = getattr(block, "content", [])

    # Normalize search result entries
    results: list[dict[str, Any]] = []
    if isinstance(search_results, list):
        for entry in search_results:
            if isinstance(entry, dict):
                results.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("url", ""),
                        "snippet": entry.get("encrypted_content", entry.get("text", "")),
                    }
                )
            else:
                results.append(
                    {
                        "title": getattr(entry, "title", ""),
                        "url": getattr(entry, "url", ""),
                        "snippet": getattr(
                            entry,
                            "encrypted_content",
                            getattr(entry, "text", ""),
                        ),
                    }
                )

    result_data: dict[str, Any] = {
        "toolCallId": str(tool_id),
        "output": {"type": "web_search_results", "results": results},
        "status": "completed",
    }
    return f"event: tool_result\ndata: {json.dumps(result_data)}\n\n"


def _get_block_type(block: Any) -> str:
    """Extract block type from SDK content block.

    SDK blocks can be dicts or typed objects (TextBlock, ThinkingBlock).
    """
    if isinstance(block, dict):
        return str(block.get("type", "text"))
    return str(getattr(block, "type", "text"))


def _get_block_text(block: Any, attr: str = "text") -> str:
    """Extract text from SDK content block by attribute name."""
    if isinstance(block, dict):
        return str(block.get(attr, block.get("text", "")))
    return str(getattr(block, attr, getattr(block, "text", "")))


def transform_tool_result(
    message: Message,
    tool_input: dict[str, Any] | None = None,
) -> str | None:
    """Transform MCP tool result to SSE event (content_update for note tools, tool_result for others).

    Args:
        message: SDK ToolResultMessage or ToolResult object.
        tool_input: Optional original tool input dict for frontend display.
    """
    result_data = getattr(message, "result", {})
    tool_use_id = getattr(message, "tool_use_id", "")

    # Handle note tool content_update operations
    if isinstance(result_data, dict) and result_data.get("status") == "pending_apply":
        operation = result_data.get("operation")
        note_id = result_data.get("note_id")

        if not note_id or not isinstance(note_id, str):
            logger.warning(
                f"Tool result missing valid note_id: operation={operation}, note_id={note_id}"
            )
            return None

        if not operation or not isinstance(operation, str):
            return None

        operation_handlers = {
            "replace_block": emit_replace_block_event,
            "append_blocks": emit_append_blocks_event,
            "create_issues": emit_issue_creation_events,
            "create_single_issue": emit_issue_creation_events,
            "insert_blocks": emit_insert_blocks_event,
            "remove_block": emit_remove_block_event,
            "remove_content": emit_remove_content_event,
            "replace_content": emit_replace_content_event,
        }

        handler = operation_handlers.get(operation)
        content_update_event = handler(result_data, note_id) if handler else None
        if not content_update_event:
            return None
        # Also emit tool_result so frontend ToolCallCard shows completion
        output_summary: dict[str, Any] = {
            "operation": operation,
            "noteId": note_id,
        }
        block_id = result_data.get("block_id")
        if block_id:
            output_summary["blockId"] = block_id
        tool_result_event = f"event: tool_result\ndata: {
            json.dumps(
                {
                    'toolCallId': str(tool_use_id) if tool_use_id else str(uuid4()),
                    'status': 'completed',
                    'output': output_summary,
                }
            )
        }\n\n"
        return f"{content_update_event}{tool_result_event}"

    # Map TodoWrite results to task_progress SSE events (T6/G-07)
    tool_name = getattr(message, "name", "") or getattr(message, "tool_name", "")
    todo_event = transform_todo_to_task_progress(tool_name, result_data, tool_use_id)
    if todo_event:
        return todo_event

    # Emit generic tool_result event for non-content tools
    is_error = False
    output = result_data
    error_message: str | None = None

    if isinstance(result_data, dict):
        is_error = result_data.get("is_error", False) is True
        error_message = result_data.get("error") if is_error else None
    elif isinstance(result_data, str) and result_data.startswith("Error"):
        is_error = True
        error_message = result_data

    tool_result_data: dict[str, Any] = {
        "toolCallId": str(tool_use_id) if tool_use_id else str(uuid4()),
        "status": "failed" if is_error else "completed",
    }
    if tool_input:
        tool_result_data["toolInput"] = tool_input
    if not is_error:
        tool_result_data["output"] = output
    if error_message:
        tool_result_data["errorMessage"] = error_message

    return f"event: tool_result\ndata: {json.dumps(tool_result_data, default=str)}\n\n"
