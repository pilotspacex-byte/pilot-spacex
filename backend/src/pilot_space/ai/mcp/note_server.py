"""In-process SDK custom tools for PilotSpace note manipulation.

Creates an SDK MCP server using create_sdk_mcp_server() with 9 note tools.
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
    f"mcp__{SERVER_NAME}__extract_issues",
    f"mcp__{SERVER_NAME}__create_issue_from_note",
    f"mcp__{SERVER_NAME}__link_existing_issues",
    f"mcp__{SERVER_NAME}__write_to_note",
    f"mcp__{SERVER_NAME}__search_notes",
    f"mcp__{SERVER_NAME}__create_note",
    f"mcp__{SERVER_NAME}__update_note",
]


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format an SSE event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def create_note_tools_server(
    event_queue: asyncio.Queue[str],
    *,
    context_note_id: str | None = None,
    tool_context: Any | None = None,
) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server with 9 note tools.

    Each tool handler pushes content_update SSE events to event_queue
    and returns a success message for the model to continue with.

    Args:
        event_queue: Queue for SSE events consumed by the stream method.
        context_note_id: The actual note_id from the chat context.
            Overrides model-provided note_id in all events to prevent
            UUID corruption by the LLM.
        tool_context: ToolContext for database access and RLS enforcement.

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

    @tool(
        "search_notes",
        "Search for notes by title in the workspace. Returns matching notes with metadata.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for note title"},
                "project_id": {
                    "type": "string",
                    "description": "Optional project UUID to filter by",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum number of results (max 100)",
                },
                "include_content": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include content preview in results",
                },
            },
            "required": ["query"],
        },
    )
    async def search_notes(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: tool_context not available for search_notes")

        from uuid import UUID

        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )

        try:
            workspace_id = UUID(tool_context.workspace_id)
            query = args["query"]
            project_id_str = args.get("project_id")
            project_id = UUID(project_id_str) if project_id_str else None
            limit = min(args.get("limit", 20), 100)
            include_content = args.get("include_content", False)

            repo = NoteRepository(tool_context.db_session)
            notes = await repo.search_by_title(
                workspace_id=workspace_id,
                search_term=query,
                project_id=project_id,
                limit=limit,
            )

            results = []
            for note in notes:
                result_item = {
                    "id": str(note.id),
                    "title": note.title,
                    "project_id": str(note.project_id) if note.project_id else None,
                    "created_at": note.created_at.isoformat(),
                }
                if include_content:
                    content = note.content or {}
                    blocks = content.get("content", [])
                    preview_text = ""
                    for block in blocks[:3]:
                        if block.get("type") == "paragraph":
                            for node in block.get("content", []):
                                if node.get("type") == "text":
                                    preview_text += node.get("text", "")
                        if len(preview_text) > 200:
                            break
                    result_item["content_preview"] = preview_text[:200]
                results.append(result_item)

            logger.info("[NoteTools] search_notes: query='%s', found=%d", query, len(results))
            return _text_result(
                f"Found {len(results)} note(s) matching '{query}':\n"
                + "\n".join(f"- {r['title']} ({r['id']})" for r in results)
            )
        except Exception as e:
            logger.exception("[NoteTools] search_notes failed")
            return _text_result(f"Error searching notes: {e!s}")

    @tool(
        "create_note",
        "Create a new note in the workspace.",
        {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Note title (1-255 characters)",
                },
                "content_markdown": {
                    "type": "string",
                    "description": "Optional markdown content for the note",
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project UUID to associate with",
                },
            },
            "required": ["title"],
        },
    )
    async def create_note(args: dict[str, Any]) -> dict[str, Any]:
        title = args.get("title", "").strip()
        if not title or len(title) > 255:
            return _text_result("Error: title must be 1-255 characters")

        payload: dict[str, Any] = {"title": title}
        if "content_markdown" in args:
            payload["content_markdown"] = args["content_markdown"]
        if "project_id" in args:
            payload["project_id"] = args["project_id"]

        logger.info("[NoteTools] create_note: title='%s'", title)
        return {
            "status": "approval_required",
            "operation": "create_note",
            "payload": payload,
        }

    @tool(
        "update_note",
        "Update note metadata (title, pinned status, project association).",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note to update"},
                "title": {
                    "type": "string",
                    "description": "New title (1-255 characters)",
                },
                "is_pinned": {
                    "type": "boolean",
                    "description": "Pin or unpin the note",
                },
                "project_id": {
                    "type": ["string", "null"],
                    "description": "Project UUID to associate, or null to unlink",
                },
            },
            "required": ["note_id"],
        },
    )
    async def update_note(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id")
        if not note_id:
            return _text_result("Error: note_id is required")

        changes: dict[str, Any] = {}
        if "title" in args:
            title = args["title"].strip()
            if not title or len(title) > 255:
                return _text_result("Error: title must be 1-255 characters")
            changes["title"] = title
        if "is_pinned" in args:
            changes["is_pinned"] = bool(args["is_pinned"])
        if "project_id" in args:
            changes["project_id"] = args["project_id"]

        if not changes:
            return _text_result("Error: no changes specified")

        logger.info("[NoteTools] update_note: note_id=%s, changes=%s", note_id, changes)
        return {
            "status": "approval_required",
            "operation": "update_note",
            "payload": {"note_id": note_id, "changes": changes},
        }

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            update_note_block,
            enhance_text,
            write_to_note,
            extract_issues,
            create_issue_from_note,
            link_existing_issues,
            search_notes,
            create_note,
            update_note,
        ],
    )


def _text_result(text: str) -> dict[str, Any]:
    """Create a standard MCP tool text result."""
    return {"content": [{"type": "text", "text": text}]}
