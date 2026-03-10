"""In-process SDK MCP server with 9 note tools.

Mutation tools emit SSE events directly via EventPublisher and return
short text confirmations to avoid echoing content back as LLM input tokens.
Note IDs are overridden from agent context (not model args) to prevent
LLM UUID corruption.
Read-only search tools (search_notes) live in note_query_server.py (CQRS-lite split).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.ai.infrastructure.approval import ActionType as AT
from pilot_space.ai.mcp.event_publisher import EventPublisher
from pilot_space.ai.tools.mcp_server import check_approval_from_db
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.mcp.block_ref_map import BlockRefMap

logger = get_logger(__name__)

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
    f"mcp__{SERVER_NAME}__insert_pm_block",
    f"mcp__{SERVER_NAME}__create_note",
    f"mcp__{SERVER_NAME}__update_note",
]


def create_note_tools_server(
    publisher: EventPublisher,
    *,
    context_note_id: str | None = None,
    tool_context: Any | None = None,
    block_ref_map: BlockRefMap | None = None,
) -> McpSdkServerConfig:
    """Create SDK MCP server with 9 note tools.

    Args:
        publisher: EventPublisher for SSE event delivery.
        context_note_id: Overrides model-provided note_id to prevent UUID corruption.
        tool_context: ToolContext for DB access and RLS enforcement.
        block_ref_map: ¶N block reference map for human-readable references.
    """
    _chk = check_approval_from_db

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
            return "Error: authentication context required for this operation"
        if not note_id:
            return "note_id is required"
        from uuid import UUID

        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )

        try:
            repo = NoteRepository(tool_context.db_session)
            exists = await repo.exists_in_workspace(UUID(note_id), UUID(tool_context.workspace_id))
        except (ValueError, TypeError):
            return f"Invalid note_id: {note_id}"
        if not exists:
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
        block_id = _resolve_block_ref(args["block_id"])

        ws_err = await _verify_note_workspace(note_id)
        if ws_err:
            return _text_result(f"Error: {ws_err}")

        ai_op = "replace_block" if operation == "replace" else "append_blocks"
        logger.info(
            "mcp_tool_invoked", tool="update_note_block", operation=ai_op, block_id=block_id
        )
        lvl = await _chk("update_note_block", AT.REPLACE_CONTENT, tool_context)
        status = "approval_required" if lvl.value != "auto_execute" else "pending_apply"
        await publisher.publish_focus_and_content(
            note_id,
            block_id,
            {
                "status": status,
                "operation": ai_op,
                "noteId": note_id,
                "blockId": block_id,
                "markdown": args["new_content_markdown"],
                "afterBlockId": block_id if ai_op == "append_blocks" else None,
            },
        )
        return _text_result(f"Block ¶{block_id[:8]} {ai_op.replace('_', ' ')}d.")

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
        block_id = _resolve_block_ref(args["block_id"])

        ws_err = await _verify_note_workspace(note_id)
        if ws_err:
            return _text_result(f"Error: {ws_err}")
        logger.info("mcp_tool_invoked", tool="enhance_text", block_id=block_id)
        lvl = await _chk("enhance_text", None, tool_context)
        status = "approval_required" if lvl.value != "auto_execute" else "pending_apply"
        await publisher.publish_focus_and_content(
            note_id,
            block_id,
            {
                "status": status,
                "operation": "replace_block",
                "noteId": note_id,
                "blockId": block_id,
                "markdown": args["enhanced_markdown"],
            },
        )
        return _text_result(f"Block ¶{block_id[:8]} enhanced.")

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
        logger.info("mcp_tool_invoked", tool="write_to_note", note_id=note_id)
        lvl = await _chk("write_to_note", AT.REPLACE_CONTENT, tool_context)
        status = "approval_required" if lvl.value != "auto_execute" else "pending_apply"
        await publisher.publish_focus_and_content(
            note_id,
            None,
            {
                "status": status,
                "operation": "append_blocks",
                "noteId": note_id,
                "markdown": markdown,
                "afterBlockId": None,
            },
            scroll_to_end=True,
        )
        return _text_result("Content appended to note.")

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
                        "required": ["title", "description"],
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
                    "title": issue["title"],
                    "description": issue["description"],
                    "priority": issue.get("priority", "medium"),
                    "type": issue.get("type", "task"),
                }
            )

        count = len(issues)
        logger.info("mcp_tool_invoked", tool="extract_issues", issue_count=count, note_id=note_id)
        lvl = await _chk("extract_issues", AT.EXTRACT_ISSUES, tool_context)
        status = "approval_required" if lvl.value != "auto_execute" else "pending_apply"
        await publisher.publish_focus_and_content(
            note_id,
            block_ids[0] if block_ids else None,
            {
                "status": status,
                "operation": "create_issues",
                "noteId": note_id,
                "issues": normalized_issues,
                "blockIds": block_ids,
            },
        )
        return _text_result(f"Extracted {count} issue(s) from note.")

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
        block_id = _resolve_block_ref(args["block_id"])

        ws_err = await _verify_note_workspace(note_id)
        if ws_err:
            return _text_result(f"Error: {ws_err}")
        issue_data = {
            "title": args["title"],
            "description": args["description"],
            "priority": args.get("priority", "medium"),
            "type": args.get("issue_type", "task"),
        }
        logger.info(
            "mcp_tool_invoked",
            tool="create_issue_from_note",
            title=args["title"][:80],
            block_id=block_id,
        )
        lvl = await _chk("create_issue_from_note", AT.CREATE_ISSUE, tool_context)
        status = "approval_required" if lvl.value != "auto_execute" else "pending_apply"
        await publisher.publish_focus_and_content(
            note_id,
            block_id,
            {
                "status": status,
                "operation": "create_single_issue",
                "noteId": note_id,
                "blockId": block_id,
                "issue": issue_data,
            },
        )
        return _text_result(f"Issue '{args['title'][:50]}' created from ¶{block_id[:8]}.")

    @tool(
        "link_existing_issues",
        "Search for existing issues in the workspace and return candidates "
        "to link to the current note. Read-only search operation.",
        {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "UUID of the note to link issues to",
                },
                "search_query": {
                    "type": "string",
                    "description": "Search query to find matching issues",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "maximum": 50,
                    "description": "Maximum number of results",
                },
            },
            "required": ["note_id", "search_query"],
        },
    )
    async def link_existing_issues(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: tool_context not available")

        from uuid import UUID

        from pilot_space.infrastructure.database.repositories.issue_repository import (
            IssueRepository,
        )

        note_id = args["note_id"]
        ws_err = await _verify_note_workspace(note_id)
        if ws_err:
            return _text_result(f"Error: {ws_err}")

        try:
            workspace_id = UUID(tool_context.workspace_id)
            query = args["search_query"]
            limit = min(args.get("limit", 10), 50)

            repo = IssueRepository(tool_context.db_session)
            issues = await repo.search_issues(
                workspace_id=workspace_id,
                search_term=query,
                limit=limit,
            )

            results = [
                {
                    "id": str(issue.id),
                    "name": issue.name,
                    "state": issue.state.name if issue.state else "Unknown",
                    "project": (issue.project.identifier if issue.project else None),
                }
                for issue in issues
            ]

            logger.info(
                "mcp_tool_invoked",
                tool="link_existing_issues",
                query=query[:50],
                found=len(results),
            )

            if not results:
                return _text_result(f"No issues found matching '{query}'.")

            return _text_result(
                f"Found {len(results)} issue(s) matching '{query}':\n"
                + json.dumps(results, indent=2)
            )
        except Exception as e:
            logger.exception("mcp_tool_error", tool="link_existing_issues")
            return _text_result(f"Error searching issues: {e!s}")

    _VALID_PM_BLOCK_TYPES = frozenset(
        {
            "raci",
            "risk",
            "decision",
            "dependency",
            "assumption",
            "requirement",
            "acceptance_criteria",
            "user_story",
            "definition_of_done",
            "status_update",
        }
    )

    _PM_BLOCK_SCHEMAS: dict[str, set[str]] = {
        "raci": {"roles", "responsibilities"},
        "risk": {"description", "likelihood", "impact", "mitigation"},
        "decision": {"summary", "rationale", "alternatives"},
        "dependency": {"dependsOn", "blockedBy", "type"},
        "assumption": {"statement", "owner", "validationDate"},
        "requirement": {"title", "description", "priority", "acceptanceCriteria"},
        "acceptance_criteria": {"criteria"},
        "user_story": {"asA", "iWant", "soThat", "acceptanceCriteria"},
        "definition_of_done": {"items"},
        "status_update": {"status", "summary", "nextSteps"},
    }

    @tool(
        "insert_pm_block",
        "Insert a PM block (decision, risk, raci, etc.) into a note. "
        "block_type must be one of: raci, risk, decision, dependency, assumption, "
        "requirement, acceptance_criteria, user_story, definition_of_done, status_update. "
        "data must be a valid JSON string with block-type-specific fields. "
        "after_block_id is an optional ¶N reference or UUID to insert after.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_type": {
                    "type": "string",
                    "enum": [
                        "raci",
                        "risk",
                        "decision",
                        "dependency",
                        "assumption",
                        "requirement",
                        "acceptance_criteria",
                        "user_story",
                        "definition_of_done",
                        "status_update",
                    ],
                    "description": "PM block type to insert",
                },
                "data": {
                    "type": "string",
                    "description": "JSON string with block-type-specific data fields",
                },
                "after_block_id": {
                    "type": "string",
                    "description": "Optional block reference (¶N) or UUID to insert after",
                },
            },
            "required": ["note_id", "block_type", "data"],
        },
    )
    async def insert_pm_block(args: dict[str, Any]) -> dict[str, Any]:
        note_id = _resolve_note_id(args)

        ws_err = await _verify_note_workspace(note_id)
        if ws_err:
            return _text_result(f"Error: {ws_err}")

        block_type = args.get("block_type", "")
        if block_type not in _VALID_PM_BLOCK_TYPES:
            return _text_result(
                f"Error: Invalid block_type '{block_type}'. "
                f"Must be one of: {', '.join(sorted(_VALID_PM_BLOCK_TYPES))}"
            )

        data_str = args.get("data", "")
        try:
            parsed_data = json.loads(data_str)
        except (json.JSONDecodeError, TypeError):
            return _text_result("Error: data must be a valid JSON string")

        if isinstance(parsed_data, dict):
            expected_keys = _PM_BLOCK_SCHEMAS.get(block_type, set())
            supplied_keys = set(parsed_data.keys())
            unknown_keys = supplied_keys - expected_keys
            if unknown_keys:
                logger.warning(
                    "mcp_tool_warn",
                    tool="insert_pm_block",
                    block_type=block_type,
                    unknown_keys=sorted(unknown_keys),
                )
            missing_keys = expected_keys - supplied_keys
            if missing_keys:
                logger.warning(
                    "mcp_tool_warn",
                    tool="insert_pm_block",
                    block_type=block_type,
                    missing_keys=sorted(missing_keys),
                )

        after_block_id_raw = args.get("after_block_id")
        after_block_id = _resolve_block_ref(after_block_id_raw) if after_block_id_raw else None

        logger.info(
            "mcp_tool_invoked",
            tool="insert_pm_block",
            block_type=block_type,
            note_id=note_id,
        )
        lvl = await _chk("insert_pm_block", AT.INSERT_BLOCK, tool_context)
        status = "approval_required" if lvl.value != "auto_execute" else "pending_apply"
        await publisher.publish_focus_and_content(
            note_id,
            after_block_id,
            {
                "status": status,
                "operation": "insert_pm_block",
                "noteId": note_id,
                "afterBlockId": after_block_id,
                "pmBlockData": {"blockType": block_type, "data": data_str, "version": 1},
            },
        )
        return _text_result(f"PM block '{block_type}' inserted into note.")

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

        logger.info("mcp_tool_invoked", tool="create_note", title=title[:80])
        lvl = await _chk("create_note", AT.CREATE_NOTE, tool_context)
        status = "approval_required" if lvl.value != "auto_execute" else "pending_apply"
        return _text_result(
            json.dumps(
                {
                    "status": status,
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

        if error := await _verify_note_workspace(note_id):
            return _text_result(f"Error: {error}")

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

        logger.info("mcp_tool_invoked", tool="update_note", note_id=note_id, changes=changes)
        lvl = await _chk("update_note", AT.UPDATE_NOTE, tool_context)
        status = "approval_required" if lvl.value != "auto_execute" else "pending_apply"
        return _text_result(
            json.dumps(
                {
                    "status": status,
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
            insert_pm_block,
            create_note,
            update_note,
        ],
    )


def _text_result(text: str) -> dict[str, Any]:
    """Create a standard MCP tool text result."""
    return {"content": [{"type": "text", "text": text}]}
