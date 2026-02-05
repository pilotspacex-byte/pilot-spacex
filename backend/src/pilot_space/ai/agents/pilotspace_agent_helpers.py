"""Helper functions for PilotSpace Agent.

SSE event emission, message transformation utilities, and subagent definitions.
Extracted from pilotspace_agent.py for modularity (file size quality gate).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from claude_agent_sdk import AgentDefinition

from pilot_space.ai.agents.pilotspace_note_helpers import (
    emit_append_blocks_event,
    emit_issue_creation_events,
    emit_replace_block_event,
    transform_todo_to_task_progress,
    transform_user_message_tool_results,
    validate_structured_output,
)
from pilot_space.ai.agents.stream_event_transformer import transform_stream_event

if TYPE_CHECKING:
    from claude_agent_sdk import Message

    from pilot_space.ai.agents.pilotspace_agent import ChatInput

logger = logging.getLogger(__name__)


def build_subagent_definitions() -> dict[str, AgentDefinition]:
    """Build subagent definitions for SDK agent spawning.

    Each subagent has a dedicated model, tool set, and detailed prompt
    aligned with provider routing per DD-011.
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


def build_contextual_message(input_data: ChatInput) -> str:
    """Enrich user message with note/issue context for the SDK.

    Includes note_id and block_ids so the model can call note tools
    (extract_issues, update_note_block, etc.) with correct parameters.
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
        if selected_block_ids:
            note_header += (
                f"\nselected_block_ids: {', '.join(str(bid) for bid in selected_block_ids)}"
            )

        if note_content:
            from pilot_space.application.services.note.content_converter import (
                ContentConverter,
            )

            converter = ContentConverter()
            markdown = converter.tiptap_to_markdown(note_content)
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
) -> str | None:
    """Transform Claude SDK message to frontend SSE event.

    SDK Message Types (actual attributes from claude-agent-sdk):
    - SystemMessage: data(dict), subtype — init message with session_id
    - AssistantMessage: content(list[TextBlock]), error, model — AI response
    - ResultMessage: session_id, is_error, result, usage — completion signal
    - ToolResultMessage: tool_name, result — MCP tool execution result

    Output format matches frontend SSEEvent expectations:
    - ``event: <type>\\ndata: <json>\\n\\n`` (proper SSE with event prefix)
    - camelCase field names (messageId, sessionId, delta, stopReason)

    For MCP tool results from note tools, emits content_update events.

    Args:
        message: SDK message object
        current_message_id_holder: Mutable dict with "_current_message_id" key for state

    Returns:
        SSE-formatted string or None if message should be ignored
    """
    msg_type = type(message).__name__

    if msg_type == "StreamEvent":
        event_data = getattr(message, "event", {})
        parent_tool_use_id = getattr(message, "parent_tool_use_id", None)
        return transform_stream_event(
            event_data,
            parent_tool_use_id,
            current_message_id_holder,
        )

    # Handle SDK ToolResultMessage (legacy compat) and ToolResult
    if msg_type in ("ToolResultMessage", "ToolResult"):
        return transform_tool_result(message)

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
                session_id = raw_data.get("session_id", "")
                current_message_id_holder["_current_message_id"] = str(uuid4())
                # Reset stale dedup state from previous request (prevents session leak)
                current_message_id_holder.pop("_stream_events_sent", None)
                current_message_id_holder.pop("_streamed_block_indices", None)
                data: dict[str, Any] = {
                    "messageId": current_message_id_holder["_current_message_id"],
                    "sessionId": str(session_id),
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
        stream_events_sent = bool(current_message_id_holder.pop("_stream_events_sent", False))
        raw_indices = current_message_id_holder.pop("_streamed_block_indices", None)
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
                    tool_event = _handle_tool_use_block(block, message_id)
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
                    citation_data = _extract_citation(block)
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
                            citation_data = _extract_citation(cite)
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
        session_id = getattr(message, "session_id", "")
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


def _handle_tool_use_block(block: Any, message_id: str) -> str | None:
    """Handle tool_use block from AssistantMessage content.

    Detects AskUserQuestion tool calls and emits ask_user_question SSE events.
    Other tool_use blocks emit standard tool_use SSE events.

    Args:
        block: SDK ToolUseBlock (dict or object)
        message_id: Current message ID

    Returns:
        SSE event string or None
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

    if tool_name == "AskUserQuestion":
        return _emit_ask_user_question_event(tool_id, tool_input, message_id)

    # Standard tool_use event
    tool_data: dict[str, Any] = {
        "toolCallId": str(tool_id),
        "toolName": tool_name,
        "toolInput": tool_input,
    }
    return f"event: tool_use\ndata: {json.dumps(tool_data)}\n\n"


def _handle_server_tool_use_block(block: Any) -> str | None:
    """Handle server_tool_use block (G-10).

    Server tools (web_search, web_fetch) run on Anthropic's infrastructure.
    Map to standard tool_use event so frontend renders them uniformly.
    """
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
    """Handle web_search_tool_result block (G-10).

    Emits a tool_result event with search results so the frontend
    can render them in the tool call output section.
    """
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


def _emit_ask_user_question_event(
    tool_id: str,
    tool_input: Any,
    message_id: str,
) -> str:
    """Emit ask_user_question SSE event from AskUserQuestion tool call.

    Args:
        tool_id: Tool call ID (used to submit answer back)
        tool_input: AskUserQuestion parameters (questions, options, etc.)
        message_id: Current message ID
    """
    questions = []
    if isinstance(tool_input, dict):
        raw_questions = tool_input.get("questions", [])
        if isinstance(raw_questions, list):
            for q in raw_questions:
                if isinstance(q, dict):
                    questions.append(
                        {
                            "question": q.get("question", ""),
                            "options": q.get("options", []),
                            "multiSelect": q.get("multiSelect", False),
                            "header": q.get("header", ""),
                        }
                    )

    event_data: dict[str, Any] = {
        "messageId": message_id,
        "questionId": str(tool_id),
        "questions": questions,
    }
    return f"event: ask_user_question\ndata: {json.dumps(event_data)}\n\n"


def _get_block_type(block: Any) -> str:
    """Extract block type from SDK content block.

    SDK blocks can be dicts or typed objects (TextBlock, ThinkingBlock).
    """
    if isinstance(block, dict):
        return str(block.get("type", "text"))
    return str(getattr(block, "type", "text"))


def _get_block_text(block: Any, attr: str = "text") -> str:
    """Extract text from SDK content block by attribute name.

    Args:
        block: SDK content block (dict or object)
        attr: Attribute name to read ('text' for TextBlock, 'thinking' for ThinkingBlock)
    """
    if isinstance(block, dict):
        return str(block.get(attr, block.get("text", "")))
    return str(getattr(block, attr, getattr(block, "text", "")))


def _extract_citation(block: Any) -> dict[str, Any] | None:
    """Extract citation data from SDK citation block (T58).

    Citation blocks reference source documents used in the response.
    """
    if isinstance(block, dict):
        source = block.get("source", {})
        cited_text = block.get("cited_text", block.get("text", ""))
    else:
        source = getattr(block, "source", {})
        cited_text = getattr(block, "cited_text", getattr(block, "text", ""))

    if not source and not cited_text:
        return None

    if source and not isinstance(source, dict):
        logger.warning("Citation source is not a dict: %s (type=%s)", source, type(source).__name__)
        source = {}

    source_dict: dict[str, Any] = source if isinstance(source, dict) else {}
    result: dict[str, Any] = {
        "sourceType": source_dict.get("type", "document"),
        "sourceId": source_dict.get("id", ""),
        "sourceTitle": source_dict.get("title", ""),
        "citedText": str(cited_text),
    }
    # Only include index fields when present (T70 — reduce JSON noise)
    start_idx = source_dict.get("start_index")
    end_idx = source_dict.get("end_index")
    if start_idx is not None:
        result["startIndex"] = start_idx
    if end_idx is not None:
        result["endIndex"] = end_idx
    return result


def transform_tool_result(message: Message) -> str | None:
    """Transform MCP tool result to SSE event (content_update for note tools, tool_result for others)."""
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
        }

        handler = operation_handlers.get(operation)
        content_update_event = handler(result_data, note_id) if handler else None
        if not content_update_event:
            return None
        # Also emit tool_result so frontend ToolCallCard shows completion
        tool_result_event = f"event: tool_result\ndata: {
            json.dumps(
                {
                    'toolCallId': str(tool_use_id) if tool_use_id else str(uuid4()),
                    'status': 'completed',
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
    if not is_error:
        tool_result_data["output"] = output
    if error_message:
        tool_result_data["errorMessage"] = error_message

    return f"event: tool_result\ndata: {json.dumps(tool_result_data, default=str)}\n\n"
