"""In-process SDK custom tools for PilotSpace note manipulation.

Creates an SDK MCP server using create_sdk_mcp_server() with 7 note tools.
Tool handlers push content_update SSE events to a shared asyncio.Queue
that the PilotSpaceAgent stream method interleaves with SDK messages.

The noteId in events is always overridden from the agent's context
(not from model args) because LLMs frequently corrupt long UUIDs.

Architecture:
  ClaudeSDKClient (in-process) → tool handler → pushes to event_queue
  PilotSpaceAgent._stream_with_space() → reads from event_queue + SDK messages
  Frontend useContentUpdates hook → TipTap editor updates + API calls

Reference: https://platform.claude.com/docs/en/agent-sdk/custom-tools
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

logger = logging.getLogger(__name__)

# MCP server name — used in allowed_tools as mcp__pilot-notes__{tool_name}
SERVER_NAME = "pilot-notes"

# All tool names for allowed_tools configuration
TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__update_note_block",
    f"mcp__{SERVER_NAME}__enhance_text",
    f"mcp__{SERVER_NAME}__summarize_note",
    f"mcp__{SERVER_NAME}__extract_issues",
    f"mcp__{SERVER_NAME}__create_issue_from_note",
    f"mcp__{SERVER_NAME}__link_existing_issues",
    f"mcp__{SERVER_NAME}__write_to_note",
]


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format an SSE event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def create_note_tools_server(
    event_queue: asyncio.Queue[str],
    *,
    context_note_id: str | None = None,
) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server with 7 note tools.

    Each tool handler pushes content_update SSE events to event_queue
    and returns a success message for the model to continue with.

    Args:
        event_queue: Queue for SSE events consumed by the stream method.
        context_note_id: The actual note_id from the chat context.
            Overrides model-provided note_id in all events to prevent
            UUID corruption by the LLM.

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions.mcp_servers.
    """

    def _resolve_note_id(args: dict[str, Any]) -> str:
        """Use context note_id if available, fall back to model-provided."""
        return context_note_id or args.get("note_id", "")

    @tool(
        "update_note_block",
        "Update a specific block in a note with new markdown content. "
        "Use operation='replace' to replace block content, or 'append' to add after it.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {"type": "string", "description": "ID of the block to update"},
                "new_content_markdown": {"type": "string", "description": "New markdown content"},
                "operation": {
                    "type": "string",
                    "enum": ["replace", "append"],
                    "default": "replace",
                    "description": "replace or append",
                },
            },
            "required": ["note_id", "block_id", "new_content_markdown"],
        },
    )
    async def update_note_block(args: dict[str, Any]) -> dict[str, Any]:
        operation = args.get("operation", "replace")
        if operation not in {"replace", "append"}:
            return _text_result(f"Invalid operation: {operation}. Must be 'replace' or 'append'.")

        ai_op = "replace_block" if operation == "replace" else "append_blocks"
        note_id = _resolve_note_id(args)
        event_data = {
            "noteId": note_id,
            "operation": ai_op,
            "blockId": args["block_id"],
            "markdown": args["new_content_markdown"],
            "content": None,
            "issueData": None,
            "afterBlockId": args["block_id"] if ai_op == "append_blocks" else None,
        }
        await event_queue.put(_sse_event("content_update", event_data))
        logger.info("[NoteTools] update_note_block: %s block=%s", ai_op, args["block_id"])
        return _text_result(f"Updated block {args['block_id']} ({operation}).")

    @tool(
        "enhance_text",
        "Replace a block's content with an enhanced/improved version. "
        "Use when user asks to improve, rewrite, or enhance text.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {"type": "string", "description": "ID of the block to enhance"},
                "enhanced_markdown": {"type": "string", "description": "Enhanced markdown content"},
            },
            "required": ["note_id", "block_id", "enhanced_markdown"],
        },
    )
    async def enhance_text(args: dict[str, Any]) -> dict[str, Any]:
        note_id = _resolve_note_id(args)
        event_data = {
            "noteId": note_id,
            "operation": "replace_block",
            "blockId": args["block_id"],
            "markdown": args["enhanced_markdown"],
            "content": None,
            "issueData": None,
            "afterBlockId": None,
        }
        await event_queue.put(_sse_event("content_update", event_data))
        logger.info("[NoteTools] enhance_text: block=%s", args["block_id"])
        return _text_result(f"Enhanced text in block {args['block_id']}.")

    @tool(
        "summarize_note",
        "Read the full content of a note as markdown. "
        "Always call this first before making changes.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note to read"},
            },
            "required": ["note_id"],
        },
    )
    async def summarize_note(args: dict[str, Any]) -> dict[str, Any]:
        # This is a read operation — the note content is already in the
        # context message (via _build_contextual_message). Return a hint.
        logger.info("[NoteTools] summarize_note: note=%s", _resolve_note_id(args))
        return _text_result(
            "Note content is available in the <note_context> block above. "
            "Use that content to answer the user's question."
        )

    @tool(
        "write_to_note",
        "Write new markdown content to the end of a note. "
        "Use when the user asks to draft, write, document, or add content to the note. "
        "No block_id is needed — content is appended at the end of the document.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "markdown": {
                    "type": "string",
                    "description": "Markdown content to append to the note",
                },
            },
            "required": ["note_id", "markdown"],
        },
    )
    async def write_to_note(args: dict[str, Any]) -> dict[str, Any]:
        markdown = args.get("markdown", "")
        if not markdown or not markdown.strip():
            return _text_result("Error: markdown content cannot be empty.")

        note_id = _resolve_note_id(args)
        event_data = {
            "noteId": note_id,
            "operation": "append_blocks",
            "blockId": None,
            "markdown": markdown,
            "content": None,
            "issueData": None,
            "afterBlockId": None,
        }
        await event_queue.put(_sse_event("content_update", event_data))
        logger.info("[NoteTools] write_to_note: appended to note=%s", note_id)
        return _text_result("Content written to the note successfully.")

    @tool(
        "extract_issues",
        "Extract and create multiple issues from note content. "
        "Each issue needs title, description, type (bug/task/feature/improvement), "
        "and priority (low/medium/high/urgent). Creates inline issue cards in the note.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Block IDs where issues were found",
                },
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                            },
                            "type": {
                                "type": "string",
                                "enum": ["bug", "task", "feature", "improvement"],
                            },
                        },
                        "required": ["title"],
                    },
                    "description": "Issues to create",
                },
            },
            "required": ["note_id", "block_ids", "issues"],
        },
    )
    async def extract_issues(args: dict[str, Any]) -> dict[str, Any]:
        issues = args.get("issues", [])
        block_ids = args.get("block_ids", [])
        note_id = _resolve_note_id(args)

        for idx, issue in enumerate(issues):
            block_id = block_ids[idx] if idx < len(block_ids) else None
            issue_data = {
                "title": issue.get("title", "Untitled Issue"),
                "description": issue.get("description", ""),
                "priority": issue.get("priority", "medium"),
                "type": issue.get("type", "task"),
                "sourceBlockId": block_id,
            }
            event_data = {
                "noteId": note_id,
                "operation": "insert_inline_issue",
                "blockId": block_id,
                "markdown": None,
                "content": None,
                "issueData": issue_data,
                "afterBlockId": None,
            }
            await event_queue.put(_sse_event("content_update", event_data))

        count = len(issues)
        logger.info("[NoteTools] extract_issues: %d issues from note=%s", count, note_id)
        return _text_result(f"Created {count} issue(s) as inline cards in the note.")

    @tool(
        "create_issue_from_note",
        "Create a single issue linked to a specific note block. "
        "Use for focused issue creation from one section.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {"type": "string", "description": "Block ID to link"},
                "title": {"type": "string", "description": "Issue title"},
                "description": {"type": "string", "description": "Issue description"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "default": "medium",
                },
                "issue_type": {
                    "type": "string",
                    "enum": ["bug", "task", "feature", "improvement"],
                    "default": "task",
                },
            },
            "required": ["note_id", "block_id", "title", "description"],
        },
    )
    async def create_issue_from_note(args: dict[str, Any]) -> dict[str, Any]:
        note_id = _resolve_note_id(args)
        issue_data = {
            "title": args["title"],
            "description": args["description"],
            "priority": args.get("priority", "medium"),
            "type": args.get("issue_type", "task"),
            "sourceBlockId": args["block_id"],
        }
        event_data = {
            "noteId": note_id,
            "operation": "insert_inline_issue",
            "blockId": args["block_id"],
            "markdown": None,
            "content": None,
            "issueData": issue_data,
            "afterBlockId": None,
        }
        await event_queue.put(_sse_event("content_update", event_data))
        logger.info("[NoteTools] create_issue_from_note: '%s'", args["title"])
        return _text_result(f"Created issue '{args['title']}' as inline card.")

    @tool(
        "link_existing_issues",
        "Search for existing issues and link them to the note.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "search_query": {"type": "string", "description": "Search query"},
                "workspace_id": {"type": "string", "description": "Workspace UUID"},
            },
            "required": ["note_id", "search_query", "workspace_id"],
        },
    )
    async def link_existing_issues(args: dict[str, Any]) -> dict[str, Any]:
        # Read-only search — no content_update event needed
        logger.info("[NoteTools] link_existing_issues: query='%s'", args["search_query"])
        return _text_result(
            f"Issue search for '{args['search_query']}' is not yet implemented. "
            "Please search manually in the issues list."
        )

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            update_note_block,
            enhance_text,
            summarize_note,
            write_to_note,
            extract_issues,
            create_issue_from_note,
            link_existing_issues,
        ],
    )


def _text_result(text: str) -> dict[str, Any]:
    """Create a standard MCP tool text result."""
    return {"content": [{"type": "text", "text": text}]}
