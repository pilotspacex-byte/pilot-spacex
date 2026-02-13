"""In-process SDK MCP server for note content manipulation tools.

Provides 7 tools for searching and modifying note content at the block level:
- search_note_content: Find text patterns within note blocks
- insert_block: Insert new blocks at specific positions
- remove_block: Delete a block from the note
- remove_content: Remove matching text from blocks
- replace_content: Find/replace text with regex support
- create_pm_block: Insert PM blocks (dashboard, timeline, etc.) as rich widgets
- update_pm_block: Update data of an existing PM block

Mutation tools emit SSE events directly via EventPublisher and return
short text confirmations to avoid echoing content back as LLM input tokens.

Reference: spec 010-enhanced-mcp-tools T008
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.ai.mcp.event_publisher import EventPublisher
from pilot_space.ai.tools.mcp_server import ToolContext, get_tool_approval_level
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.mcp.block_ref_map import BlockRefMap

logger = get_logger(__name__)

# MCP server name
SERVER_NAME = "pilot-note-content"

# All tool names for allowed_tools configuration
TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__search_note_content",
    f"mcp__{SERVER_NAME}__insert_block",
    f"mcp__{SERVER_NAME}__remove_block",
    f"mcp__{SERVER_NAME}__remove_content",
    f"mcp__{SERVER_NAME}__replace_content",
    f"mcp__{SERVER_NAME}__create_pm_block",
    f"mcp__{SERVER_NAME}__update_pm_block",
]

_VALID_PM_BLOCK_TYPES = frozenset({"decision", "form", "raci", "risk", "timeline", "dashboard"})

# Regex to detect a JSON code fence wrapping TipTap JSON (e.g. taskList)
_JSON_FENCE_RE = re.compile(
    r"^```(?:json)?\s*\n(.*?)\n```\s*$",
    re.DOTALL,
)


def _text_result(text: str) -> dict[str, Any]:
    """Create a standard MCP tool text result."""
    return {"content": [{"type": "text", "text": text}]}


_NESTED_QUANTIFIER_RE = re.compile(r"([+*]|\{\d+,?\d*\})\)?[+*]|\(\?[^)]*\)\+")


def _compile_search_regex(pattern: str, *, case_sensitive: bool) -> re.Pattern[str]:
    """Compile regex with ReDoS prevention. Raises re.error on invalid patterns."""
    if len(pattern) > 500:
        raise re.error("pattern exceeds maximum length of 500 characters")
    if _NESTED_QUANTIFIER_RE.search(pattern):
        raise re.error("pattern contains nested quantifiers (potential ReDoS)")
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(pattern, flags)


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
    publisher: EventPublisher,
    *,
    tool_context: ToolContext | None = None,
    block_ref_map: BlockRefMap | None = None,
) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server with 7 note content tools.

    Mutation tools emit SSE events directly via publisher and return
    short text confirmations.

    Args:
        publisher: EventPublisher for SSE event delivery.
        tool_context: ToolContext for database access and RLS enforcement.
        block_ref_map: Optional ¶N block reference map for human-readable
            block references.

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions.mcp_servers.
    """

    def _resolve_block_ref(ref_or_id: str) -> str:
        """Resolve ¶N reference to UUID if block_ref_map is available."""
        if block_ref_map is not None:
            return block_ref_map.resolve(ref_or_id)
        return ref_or_id

    def _format_block_ref(block_id: str) -> str:
        """Format block UUID as human-readable ¶N reference."""
        if block_ref_map is not None:
            return block_ref_map.format_ref(block_id)
        return block_id

    async def _verify_note_workspace(note_id: str | None) -> str | None:
        """Verify note belongs to current workspace. Returns error message or None."""
        if not tool_context:
            return "tool_context not available"
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

            # ReDoS prevention: validate length + pre-compile regex
            compiled_regex: re.Pattern[str] | None = None
            if use_regex:
                try:
                    compiled_regex = _compile_search_regex(pattern, case_sensitive=case_sensitive)
                except re.error as e:
                    return _text_result(f"Error: Invalid regex pattern: {e}")

            for line_num, block in enumerate(blocks, start=1):
                block_id = block.get("attrs", {}).get("id")
                block_text = _extract_block_text(block)
                if not block_text:
                    continue

                if compiled_regex is not None:
                    if compiled_regex.search(block_text):
                        context_preview = block_text[:100]
                        matches.append(
                            {
                                "block_id": block_id,
                                "text": block_text,
                                "line_number": line_num,
                                "context": context_preview,
                            }
                        )
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
                f"Line {m['line_number']} ({_format_block_ref(m['block_id'])}): {m['context']}..."
                for m in matches[:5]
            )
            more_text = f"\n... and {total - 5} more matches" if total > 5 else ""
            return _text_result(
                f"Found {total} match(es) for '{pattern}':\n{match_summary}{more_text}"
            )
        except (ValueError, TypeError, KeyError) as e:
            logger.warning("[NoteContentTools] search_note_content: %s", e)
            return _text_result(f"Error searching note content: {e!s}")

    @tool(
        "insert_block",
        "Insert new markdown content as blocks at a specific position in the note. "
        "Use ¶N references (e.g., ¶1, ¶2) for position block IDs.",
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
                    "description": "Insert after this block (¶N or UUID)",
                },
                "before_block_id": {
                    "type": "string",
                    "description": "Insert before this block (¶N or UUID)",
                },
            },
            "required": ["note_id", "content_markdown"],
        },
    )
    async def insert_block(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id")
        content_markdown = args.get("content_markdown", "").strip()
        after_block_id = (
            _resolve_block_ref(args["after_block_id"]) if args.get("after_block_id") else None
        )
        before_block_id = (
            _resolve_block_ref(args["before_block_id"]) if args.get("before_block_id") else None
        )

        ws_error = await _verify_note_workspace(note_id)
        if ws_error:
            return _text_result(f"Error: {ws_error}")

        if not content_markdown:
            return _text_result("Error: content_markdown cannot be empty")

        if after_block_id and before_block_id:
            return _text_result("Error: specify either after_block_id or before_block_id, not both")

        position = "after" if after_block_id else "before" if before_block_id else "end"

        logger.info(
            "[NoteContentTools] insert_block: note=%s, position=%s",
            note_id,
            position,
        )
        approval_level = get_tool_approval_level("insert_block")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"
        focus_id = before_block_id or after_block_id

        # Detect JSON code fence wrapping TipTap structured content (e.g. taskList).
        # Send as `content` (JSONContent) so TipTap processes it with full node attributes
        # instead of markdown which loses metadata like assignee, dueDate, priority.
        content_payload: dict[str, Any] = {
            "status": status,
            "operation": "insert_blocks",
            "noteId": note_id,
            "afterBlockId": after_block_id,
            "beforeBlockId": before_block_id,
        }

        fence_match = _JSON_FENCE_RE.match(content_markdown)
        if fence_match:
            try:
                parsed = json.loads(fence_match.group(1))
                if isinstance(parsed, dict) and parsed.get("type") in (
                    "taskList",
                    "bulletList",
                    "orderedList",
                ):
                    content_payload["content"] = parsed
                else:
                    content_payload["markdown"] = content_markdown
            except (json.JSONDecodeError, TypeError):
                content_payload["markdown"] = content_markdown
        else:
            content_payload["markdown"] = content_markdown

        await publisher.publish_focus_and_content(
            note_id or "",
            focus_id,
            content_payload,
            scroll_to_end=not focus_id,
        )
        return _text_result(f"Block inserted ({position}).")

    @tool(
        "remove_block",
        "Remove a specific block from the note. Use ¶N references (e.g., ¶1, ¶2) for block_id.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {"type": "string", "description": "Block reference (¶N) or UUID"},
            },
            "required": ["note_id", "block_id"],
        },
    )
    async def remove_block(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id")
        block_id = _resolve_block_ref(args["block_id"]) if args.get("block_id") else None

        if not block_id:
            return _text_result("Error: block_id is required")

        ws_error = await _verify_note_workspace(note_id)
        if ws_error:
            return _text_result(f"Error: {ws_error}")
        logger.info("[NoteContentTools] remove_block: note=%s, block=%s", note_id, block_id)
        approval_level = get_tool_approval_level("remove_block")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"
        await publisher.publish_focus_and_content(
            note_id or "",
            block_id,
            {
                "status": status,
                "operation": "remove_block",
                "noteId": note_id,
                "blockId": block_id,
            },
        )
        return _text_result(f"Block ¶{block_id[:8]} removed.")

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
                    "description": "Block references (¶N) or UUIDs to search (or all if omitted)",
                },
            },
            "required": ["note_id", "pattern"],
        },
    )
    async def remove_content(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id")
        pattern = args.get("pattern")
        use_regex = args.get("regex", False)
        raw_block_ids = args.get("block_ids", [])
        block_ids = [_resolve_block_ref(bid) for bid in raw_block_ids]

        ws_error = await _verify_note_workspace(note_id)
        if ws_error:
            return _text_result(f"Error: {ws_error}")

        if not pattern:
            return _text_result("Error: pattern is required")

        logger.info(
            "[NoteContentTools] remove_content: note=%s, pattern='%s', blocks=%s",
            note_id,
            pattern,
            block_ids,
        )
        approval_level = get_tool_approval_level("remove_content")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"
        await publisher.publish_focus_and_content(
            note_id or "",
            block_ids[0] if block_ids else None,
            {
                "status": status,
                "operation": "remove_content",
                "noteId": note_id,
                "pattern": pattern,
                "regex": use_regex,
                "blockIds": block_ids,
            },
        )
        return _text_result("Content removed.")

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
                    "description": "Block references (¶N) or UUIDs to modify (or all if omitted)",
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
        raw_block_ids = args.get("block_ids", [])
        block_ids = [_resolve_block_ref(bid) for bid in raw_block_ids]
        replace_all = args.get("replace_all", True)

        ws_error = await _verify_note_workspace(note_id)
        if ws_error:
            return _text_result(f"Error: {ws_error}")

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
        approval_level = get_tool_approval_level("replace_content")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"
        focus_id = block_ids[0] if block_ids else None
        await publisher.publish_focus_and_content(
            note_id or "",
            focus_id,
            {
                "status": status,
                "operation": "replace_content",
                "noteId": note_id,
                "oldPattern": old_pattern,
                "newContent": new_content,
                "regex": use_regex,
                "blockIds": block_ids,
                "replaceAll": replace_all,
            },
        )
        return _text_result("Content replaced.")

    @tool(
        "create_pm_block",
        "Insert a PM block (dashboard, timeline, decision, form, raci, risk) "
        "as a rich widget. Use ¶N references for after_block_id.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_type": {
                    "type": "string",
                    "enum": sorted(_VALID_PM_BLOCK_TYPES),
                    "description": "PM block type",
                },
                "data": {
                    "type": "object",
                    "description": "Block data object (title, widgets/options/milestones, etc.)",
                },
                "after_block_id": {
                    "type": "string",
                    "description": "Insert after this block (¶N or UUID). Omit to append at end.",
                },
            },
            "required": ["note_id", "block_type", "data"],
        },
    )
    async def create_pm_block(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id")
        block_type = args.get("block_type", "")
        data_obj = args.get("data", {})
        after_block_id = (
            _resolve_block_ref(args["after_block_id"]) if args.get("after_block_id") else None
        )

        if not data_obj:
            return _text_result("Error: data cannot be empty")

        ws_error = await _verify_note_workspace(note_id)
        if ws_error:
            return _text_result(f"Error: {ws_error}")

        if block_type not in _VALID_PM_BLOCK_TYPES:
            return _text_result(
                f"Error: invalid block_type '{block_type}'. "
                f"Must be one of: {', '.join(sorted(_VALID_PM_BLOCK_TYPES))}"
            )

        logger.info(
            "[NoteContentTools] create_pm_block: note=%s, type=%s",
            note_id,
            block_type,
        )
        approval_level = get_tool_approval_level("insert_block")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"
        await publisher.publish_focus_and_content(
            note_id or "",
            after_block_id,
            {
                "status": status,
                "operation": "insert_pm_block",
                "noteId": note_id,
                "pmBlockData": {
                    "blockType": block_type,
                    "data": json.dumps(data_obj),
                    "version": 1,
                },
                "afterBlockId": after_block_id,
            },
            scroll_to_end=not after_block_id,
        )
        return _text_result(f"PM block ({block_type}) inserted.")

    @tool(
        "update_pm_block",
        "Update the data of an existing PM block. Use ¶N references for block_id.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {
                    "type": "string",
                    "description": "Block reference (¶N) or UUID of the PM block to update",
                },
                "data": {
                    "type": "object",
                    "description": "Updated block data object",
                },
                "block_type": {
                    "type": "string",
                    "enum": sorted(_VALID_PM_BLOCK_TYPES),
                    "description": "PM block type (optional, for type change)",
                },
            },
            "required": ["note_id", "block_id", "data"],
        },
    )
    async def update_pm_block(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id")
        block_id = _resolve_block_ref(args["block_id"]) if args.get("block_id") else None
        data_obj = args.get("data", {})
        block_type = args.get("block_type")

        if not block_id:
            return _text_result("Error: block_id is required")

        if not data_obj:
            return _text_result("Error: data cannot be empty")

        ws_error = await _verify_note_workspace(note_id)
        if ws_error:
            return _text_result(f"Error: {ws_error}")

        if block_type and block_type not in _VALID_PM_BLOCK_TYPES:
            return _text_result(
                f"Error: invalid block_type '{block_type}'. "
                f"Must be one of: {', '.join(sorted(_VALID_PM_BLOCK_TYPES))}"
            )

        logger.info(
            "[NoteContentTools] update_pm_block: note=%s, block=%s",
            note_id,
            block_id,
        )
        approval_level = get_tool_approval_level("update_pm_block")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"

        pm_block_data: dict[str, Any] = {
            "data": json.dumps(data_obj),
            "version": 1,
        }
        if block_type:
            pm_block_data["blockType"] = block_type

        await publisher.publish_focus_and_content(
            note_id or "",
            block_id,
            {
                "status": status,
                "operation": "update_pm_block",
                "noteId": note_id,
                "blockId": block_id,
                "pmBlockData": pm_block_data,
            },
        )
        return _text_result(f"PM block {block_id[:8]} updated.")

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            search_note_content,
            insert_block,
            remove_block,
            remove_content,
            replace_content,
            create_pm_block,
            update_pm_block,
        ],
    )
