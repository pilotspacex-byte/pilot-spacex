"""In-process SDK custom tools for PilotSpace note manipulation.

Creates an SDK MCP server using create_sdk_mcp_server() with 9 note tools.
Mutation tools return structured JSON payloads (status: pending_apply) that
the SDK pipeline transforms into SSE content_update events via
transform_user_message_tool_results() in pilotspace_note_helpers.py.

The noteId in events is always overridden from the agent's context
(not from model args) because LLMs frequently corrupt long UUIDs.

Architecture:
  ClaudeSDKClient (in-process) → tool handler → returns pending_apply JSON
  SDK pipeline → transform_user_message_tool_results() → content_update SSE
  Frontend useContentUpdates hook → TipTap editor updates + API calls

Reference: https://platform.claude.com/docs/en/agent-sdk/custom-tools
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

if TYPE_CHECKING:
    from pilot_space.ai.mcp.block_ref_map import BlockRefMap

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


def create_note_tools_server(
    event_queue: asyncio.Queue[str],
    *,
    context_note_id: str | None = None,
    tool_context: Any | None = None,
    block_ref_map: BlockRefMap | None = None,
) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server with 9 note tools.

    Mutation tools return structured JSON payloads (status: pending_apply)
    that the SDK pipeline transforms into SSE content_update events.
    The event_queue parameter is retained for backward compatibility but
    is no longer used by note tools (content_update events flow through
    the SDK tool_result pipeline instead).

    Args:
        event_queue: Queue retained for API compatibility; not used by note tools.
        context_note_id: The actual note_id from the chat context.
            Overrides model-provided note_id in all events to prevent
            UUID corruption by the LLM.
        tool_context: ToolContext for database access and RLS enforcement.
        block_ref_map: Optional ¶N block reference map for human-readable
            block references. When provided, tool handlers resolve ¶N
            references to UUIDs and use ¶N notation in result text.

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions.mcp_servers.
    """

    def _resolve_note_id(args: dict[str, Any]) -> str:
        """Use context note_id if available, fall back to model-provided."""
        return context_note_id or args.get("note_id", "")

    def _resolve_block_ref(ref_or_id: str) -> str:
        """Resolve ¶N reference to UUID if block_ref_map is available."""
        if block_ref_map is not None:
            return block_ref_map.resolve(ref_or_id)
        return ref_or_id

    async def _verify_note_workspace(note_id: str) -> str | None:
        """Verify note belongs to current workspace. Returns error message or None."""
        if not tool_context:
            return None  # No context available; skip verification (test/dev mode)
        if not note_id:
            return "note_id is required"
        from uuid import UUID

        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )

        try:
            repo = NoteRepository(tool_context.db_session)
            note = await repo.get_by_id(UUID(note_id))
        except (ValueError, TypeError):
            return f"Invalid note_id: {note_id}"
        if not note or str(note.workspace_id) != tool_context.workspace_id:
            return f"Note {note_id} not found in workspace"
        return None

    @tool(
        "update_note_block",
        "Update a specific block in a note with new markdown content. "
        "Use operation='replace' to replace block content, or 'append' to add after it. "
        "Use ¶N references (e.g., ¶1, ¶2) for block_id.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {"type": "string", "description": "Block reference (¶N) or UUID"},
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

        note_id = _resolve_note_id(args)
        ws_err = await _verify_note_workspace(note_id)
        if ws_err:
            return _text_result(f"Error: {ws_err}")

        block_id = _resolve_block_ref(args["block_id"])
        ai_op = "replace_block" if operation == "replace" else "append_blocks"
        logger.info("[NoteTools] update_note_block: %s block=%s", ai_op, block_id)
        return _text_result(
            json.dumps(
                {
                    "status": "pending_apply",
                    "operation": ai_op,
                    "note_id": note_id,
                    "block_id": block_id,
                    "markdown": args["new_content_markdown"],
                    "after_block_id": block_id if ai_op == "append_blocks" else None,
                }
            )
        )

    @tool(
        "enhance_text",
        "Replace a block's content with an enhanced/improved version. "
        "Use when user asks to improve, rewrite, or enhance text. "
        "Use ¶N references (e.g., ¶1, ¶2) for block_id.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {"type": "string", "description": "Block reference (¶N) or UUID"},
                "enhanced_markdown": {"type": "string", "description": "Enhanced markdown content"},
            },
            "required": ["note_id", "block_id", "enhanced_markdown"],
        },
    )
    async def enhance_text(args: dict[str, Any]) -> dict[str, Any]:
        note_id = _resolve_note_id(args)
        ws_err = await _verify_note_workspace(note_id)
        if ws_err:
            return _text_result(f"Error: {ws_err}")

        block_id = _resolve_block_ref(args["block_id"])
        logger.info("[NoteTools] enhance_text: block=%s", block_id)
        return _text_result(
            json.dumps(
                {
                    "status": "pending_apply",
                    "operation": "replace_block",
                    "note_id": note_id,
                    "block_id": block_id,
                    "markdown": args["enhanced_markdown"],
                }
            )
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
        ws_err = await _verify_note_workspace(note_id)
        if ws_err:
            return _text_result(f"Error: {ws_err}")
        logger.info("[NoteTools] write_to_note: appended to note=%s", note_id)
        return _text_result(
            json.dumps(
                {
                    "status": "pending_apply",
                    "operation": "append_blocks",
                    "note_id": note_id,
                    "markdown": markdown,
                    "after_block_id": None,
                }
            )
        )

    @tool(
        "extract_issues",
        "Extract and create multiple issues from note content. "
        "Each issue needs title, description, type (bug/task/feature/improvement), "
        "and priority (low/medium/high/urgent). Creates inline issue cards in the note. "
        "Use ¶N references (e.g., ¶1, ¶2) for block_ids.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Block references (¶N) or UUIDs where issues were found",
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
        raw_block_ids = args.get("block_ids", [])
        # Resolve ¶N references to UUIDs
        block_ids = [_resolve_block_ref(bid) for bid in raw_block_ids]
        note_id = _resolve_note_id(args)
        ws_err = await _verify_note_workspace(note_id)
        if ws_err:
            return _text_result(f"Error: {ws_err}")

        # Normalize issue data for the emit handler
        normalized_issues = []
        for issue in issues:
            normalized_issues.append(
                {
                    "title": issue.get("title", "Untitled Issue"),
                    "description": issue.get("description", ""),
                    "priority": issue.get("priority", "medium"),
                    "type": issue.get("type", "task"),
                }
            )

        count = len(issues)
        logger.info("[NoteTools] extract_issues: %d issues from note=%s", count, note_id)
        return _text_result(
            json.dumps(
                {
                    "status": "pending_apply",
                    "operation": "create_issues",
                    "note_id": note_id,
                    "issues": normalized_issues,
                    "block_ids": block_ids,
                }
            )
        )

    @tool(
        "create_issue_from_note",
        "Create a single issue linked to a specific note block. "
        "Use for focused issue creation from one section. "
        "Use ¶N references (e.g., ¶1, ¶2) for block_id.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {"type": "string", "description": "Block reference (¶N) or UUID"},
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
        ws_err = await _verify_note_workspace(note_id)
        if ws_err:
            return _text_result(f"Error: {ws_err}")

        block_id = _resolve_block_ref(args["block_id"])
        issue_data = {
            "title": args["title"],
            "description": args["description"],
            "priority": args.get("priority", "medium"),
            "type": args.get("issue_type", "task"),
        }
        logger.info("[NoteTools] create_issue_from_note: '%s' block=%s", args["title"], block_id)
        return _text_result(
            json.dumps(
                {
                    "status": "pending_apply",
                    "operation": "create_single_issue",
                    "note_id": note_id,
                    "block_id": block_id,
                    "issue": issue_data,
                }
            )
        )

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
        return _text_result(
            json.dumps(
                {
                    "status": "approval_required",
                    "operation": "create_note",
                    "payload": payload,
                }
            )
        )

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

        # Verify note belongs to workspace
        if tool_context:
            from uuid import UUID

            from pilot_space.infrastructure.database.repositories.note_repository import (
                NoteRepository,
            )

            try:
                repo = NoteRepository(tool_context.db_session)
                note = await repo.get_by_id(UUID(note_id))
            except (ValueError, TypeError):
                return _text_result(f"Error: Invalid note_id: {note_id}")
            if not note or str(note.workspace_id) != tool_context.workspace_id:
                return _text_result(f"Error: Note {note_id} not found in workspace")

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
        return _text_result(
            json.dumps(
                {
                    "status": "approval_required",
                    "operation": "update_note",
                    "payload": {"note_id": note_id, "changes": changes},
                }
            )
        )

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
