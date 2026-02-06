"""In-process SDK MCP server for note content manipulation tools.

Provides 5 tools for searching and modifying note content at the block level:
- search_note_content: Find text patterns within note blocks
- insert_block: Insert new blocks at specific positions
- remove_block: Delete a block from the note
- remove_content: Remove matching text from blocks
- replace_content: Find/replace text with regex support

All mutation tools return operation payloads (status: approval_required) for
frontend application via SSE content_update events.

Reference: spec 010-enhanced-mcp-tools T008
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.ai.tools.mcp_server import ToolContext

logger = logging.getLogger(__name__)

# MCP server name
SERVER_NAME = "pilot-note-content"

# All tool names for allowed_tools configuration
TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__search_note_content",
    f"mcp__{SERVER_NAME}__insert_block",
    f"mcp__{SERVER_NAME}__remove_block",
    f"mcp__{SERVER_NAME}__remove_content",
    f"mcp__{SERVER_NAME}__replace_content",
]


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format an SSE event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _text_result(text: str) -> dict[str, Any]:
    """Create a standard MCP tool text result."""
    return {"content": [{"type": "text", "text": text}]}


def _extract_block_text(block: dict[str, Any]) -> str:
    """Extract plain text from a TipTap block node."""
    text_parts: list[str] = []
    content = block.get("content", [])
    for node in content:
        if node.get("type") == "text":
            text_parts.append(node.get("text", ""))
        elif "content" in node:
            text_parts.append(_extract_block_text(node))
    return "".join(text_parts)


def create_note_content_server(
    event_queue: asyncio.Queue[str],
    *,
    tool_context: ToolContext | None = None,
) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server with 5 note content tools.

    Each tool handler pushes content_update SSE events to event_queue
    and returns operation payloads for frontend application.

    Args:
        event_queue: Queue for SSE events consumed by the stream method.
        tool_context: ToolContext for database access and RLS enforcement.

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions.mcp_servers.
    """

    @tool(
        "search_note_content",
        "Search for text patterns within note content blocks. "
        "Supports regex and case-sensitive matching.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "pattern": {"type": "string", "description": "Text pattern to search for"},
                "regex": {
                    "type": "boolean",
                    "default": False,
                    "description": "Treat pattern as regex",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "default": False,
                    "description": "Case-sensitive search",
                },
            },
            "required": ["note_id", "pattern"],
        },
    )
    async def search_note_content(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: tool_context not available for search_note_content")

        from uuid import UUID

        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )

        try:
            note_id = UUID(args["note_id"])
            pattern = args["pattern"]
            use_regex = args.get("regex", False)
            case_sensitive = args.get("case_sensitive", False)

            repo = NoteRepository(tool_context.db_session)
            note = await repo.get_by_id(note_id)
            if not note or str(note.workspace_id) != tool_context.workspace_id:
                return _text_result(f"Error: Note {note_id} not found in workspace")

            content = note.content or {}
            blocks = content.get("content", [])
            matches: list[dict[str, Any]] = []

            for line_num, block in enumerate(blocks, start=1):
                block_id = block.get("attrs", {}).get("id")
                block_text = _extract_block_text(block)
                if not block_text:
                    continue

                if use_regex:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    try:
                        if re.search(pattern, block_text, flags):
                            context_preview = block_text[:100]
                            matches.append(
                                {
                                    "block_id": block_id,
                                    "text": block_text,
                                    "line_number": line_num,
                                    "context": context_preview,
                                }
                            )
                    except re.error as e:
                        return _text_result(f"Error: Invalid regex pattern: {e}")
                else:
                    search_pattern = pattern if case_sensitive else pattern.lower()
                    search_text = block_text if case_sensitive else block_text.lower()
                    if search_pattern in search_text:
                        context_preview = block_text[:100]
                        matches.append(
                            {
                                "block_id": block_id,
                                "text": block_text,
                                "line_number": line_num,
                                "context": context_preview,
                            }
                        )

            total = len(matches)
            logger.info(
                "[NoteContentTools] search_note_content: note=%s, pattern='%s', matches=%d",
                note_id,
                pattern,
                total,
            )

            if total == 0:
                return _text_result(f"No matches found for pattern '{pattern}'")

            match_summary = "\n".join(
                f"Line {m['line_number']} (block {m['block_id']}): {m['context']}..."
                for m in matches[:5]
            )
            more_text = f"\n... and {total - 5} more matches" if total > 5 else ""
            return _text_result(
                f"Found {total} match(es) for '{pattern}':\n{match_summary}{more_text}"
            )
        except Exception as e:
            logger.exception("[NoteContentTools] search_note_content failed")
            return _text_result(f"Error searching note content: {e!s}")

    @tool(
        "insert_block",
        "Insert new markdown content as blocks at a specific position in the note.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "content_markdown": {
                    "type": "string",
                    "description": "Markdown content to insert",
                },
                "after_block_id": {
                    "type": "string",
                    "description": "Insert after this block ID",
                },
                "before_block_id": {
                    "type": "string",
                    "description": "Insert before this block ID",
                },
            },
            "required": ["note_id", "content_markdown"],
        },
    )
    async def insert_block(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id")
        content_markdown = args.get("content_markdown", "").strip()
        after_block_id = args.get("after_block_id")
        before_block_id = args.get("before_block_id")

        if not content_markdown:
            return _text_result("Error: content_markdown cannot be empty")

        if after_block_id and before_block_id:
            return _text_result("Error: specify either after_block_id or before_block_id, not both")

        position = "after" if after_block_id else "before" if before_block_id else "end"
        position_block_id = after_block_id or before_block_id

        event_data = {
            "noteId": note_id,
            "operation": "insert_blocks",
            "blockId": position_block_id,
            "markdown": content_markdown,
            "content": None,
            "issueData": None,
            "afterBlockId": after_block_id,
            "beforeBlockId": before_block_id,
        }
        await event_queue.put(_sse_event("content_update", event_data))

        logger.info(
            "[NoteContentTools] insert_block: note=%s, position=%s",
            note_id,
            position,
        )
        return _text_result(
            json.dumps(
                {
                    "status": "approval_required",
                    "operation": "insert_block",
                    "payload": {
                        "note_id": note_id,
                        "content_markdown": content_markdown,
                        "after_block_id": after_block_id,
                        "before_block_id": before_block_id,
                    },
                }
            )
        )

    @tool(
        "remove_block",
        "Remove a specific block from the note by its block ID.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {"type": "string", "description": "Block ID to remove"},
            },
            "required": ["note_id", "block_id"],
        },
    )
    async def remove_block(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id")
        block_id = args.get("block_id")

        if not block_id:
            return _text_result("Error: block_id is required")

        event_data = {
            "noteId": note_id,
            "operation": "remove_block",
            "blockId": block_id,
            "markdown": None,
            "content": None,
            "issueData": None,
            "afterBlockId": None,
        }
        await event_queue.put(_sse_event("content_update", event_data))

        logger.info("[NoteContentTools] remove_block: note=%s, block=%s", note_id, block_id)
        return _text_result(
            json.dumps(
                {
                    "status": "approval_required",
                    "operation": "remove_block",
                    "payload": {"note_id": note_id, "block_id": block_id},
                }
            )
        )

    @tool(
        "remove_content",
        "Remove text matching a pattern from specified blocks or all blocks in the note.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "pattern": {"type": "string", "description": "Text pattern to remove"},
                "regex": {
                    "type": "boolean",
                    "default": False,
                    "description": "Treat pattern as regex",
                },
                "block_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific block IDs to search (or all if not specified)",
                },
            },
            "required": ["note_id", "pattern"],
        },
    )
    async def remove_content(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id")
        pattern = args.get("pattern")
        use_regex = args.get("regex", False)
        block_ids = args.get("block_ids", [])

        if not pattern:
            return _text_result("Error: pattern is required")

        logger.info(
            "[NoteContentTools] remove_content: note=%s, pattern='%s', blocks=%s",
            note_id,
            pattern,
            block_ids,
        )
        return _text_result(
            json.dumps(
                {
                    "status": "approval_required",
                    "operation": "remove_content",
                    "payload": {
                        "note_id": note_id,
                        "pattern": pattern,
                        "regex": use_regex,
                        "block_ids": block_ids,
                    },
                    "preview": f"Will remove all occurrences of '{pattern}' from note blocks",
                }
            )
        )

    @tool(
        "replace_content",
        "Find and replace text in specified blocks or all blocks. Supports regex with capture groups.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "old_pattern": {
                    "type": "string",
                    "description": "Text pattern to find",
                },
                "new_content": {
                    "type": "string",
                    "description": "Replacement text (supports $1, $2 for regex groups)",
                },
                "regex": {
                    "type": "boolean",
                    "default": False,
                    "description": "Treat pattern as regex",
                },
                "block_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific block IDs to modify (or all if not specified)",
                },
                "replace_all": {
                    "type": "boolean",
                    "default": True,
                    "description": "Replace all occurrences or just the first",
                },
            },
            "required": ["note_id", "old_pattern", "new_content"],
        },
    )
    async def replace_content(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id")
        old_pattern = args.get("old_pattern")
        new_content = args.get("new_content")
        use_regex = args.get("regex", False)
        block_ids = args.get("block_ids", [])
        replace_all = args.get("replace_all", True)

        if not old_pattern:
            return _text_result("Error: old_pattern is required")
        if new_content is None:
            return _text_result("Error: new_content is required")

        logger.info(
            "[NoteContentTools] replace_content: note=%s, old='%s', new='%s', blocks=%s",
            note_id,
            old_pattern,
            new_content,
            block_ids,
        )
        return _text_result(
            json.dumps(
                {
                    "status": "approval_required",
                    "operation": "replace_content",
                    "payload": {
                        "note_id": note_id,
                        "old_pattern": old_pattern,
                        "new_content": new_content,
                        "regex": use_regex,
                        "block_ids": block_ids,
                        "replace_all": replace_all,
                    },
                    "preview": f"Will replace '{old_pattern}' with '{new_content}' in note blocks",
                }
            )
        )

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            search_note_content,
            insert_block,
            remove_block,
            remove_content,
            replace_content,
        ],
    )
