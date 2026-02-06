"""In-process SDK custom tools for PilotSpace issue relationship operations.

Creates an SDK MCP server with 6 issue relationship tools (IS-005 to IS-010).
Tool handlers push SSE events to a shared asyncio.Queue that the PilotSpaceAgent
stream method interleaves with SDK messages.

For issue CRUD tools (IS-001 to IS-004), see issue_server.py.

Architecture:
  ClaudeSDKClient (in-process) → tool handler → pushes to event_queue
  PilotSpaceAgent._stream_with_space() → reads from event_queue + SDK messages
  Frontend stores → issue updates + API calls

Reference: spec 010-enhanced-mcp-tools Phase 3 (T010-T012)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.ai.tools.entity_resolver import resolve_entity_id
from pilot_space.ai.tools.mcp_server import ToolContext, get_tool_approval_level
from pilot_space.infrastructure.database.models.issue_link import IssueLinkType
from pilot_space.infrastructure.database.repositories.issue_repository import (
    IssueRepository,
)

logger = logging.getLogger(__name__)

# MCP server name — used in allowed_tools as mcp__pilot-issue-relations__{tool_name}
SERVER_NAME = "pilot-issue-relations"

# Tool names for relationship operations
TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__link_issue_to_note",
    f"mcp__{SERVER_NAME}__unlink_issue_from_note",
    f"mcp__{SERVER_NAME}__link_issues",
    f"mcp__{SERVER_NAME}__unlink_issues",
    f"mcp__{SERVER_NAME}__add_sub_issue",
    f"mcp__{SERVER_NAME}__transition_issue_state",
]


def _text_result(text: str) -> dict[str, Any]:
    """Create a standard MCP tool text result."""
    return {"content": [{"type": "text", "text": text}]}


def _operation_payload(
    operation: str,
    payload: dict[str, Any],
    *,
    status: str = "pending_apply",
    preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a standard operation payload for approval/execution."""
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "status": status,
                        "operation": operation,
                        "payload": payload,
                        "preview": preview,
                    }
                ),
            }
        ]
    }


async def _verify_issue_workspace(
    repo: IssueRepository,
    issue_uuid: UUID,
    workspace_id: str,
) -> str | None:
    """Verify issue belongs to workspace. Returns error message or None."""
    issue = await repo.get_by_id(issue_uuid)
    if not issue or str(issue.workspace_id) != workspace_id:
        return f"Issue {issue_uuid} not found in workspace"
    return None


async def _verify_note_workspace(
    note_id: UUID,
    tool_context: ToolContext,
) -> str | None:
    """Verify note belongs to workspace. Returns error message or None."""
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )

    repo = NoteRepository(tool_context.db_session)
    note = await repo.get_by_id(note_id)
    if not note or str(note.workspace_id) != tool_context.workspace_id:
        return f"Note {note_id} not found in workspace"
    return None


async def _check_circular_parent(
    repo: IssueRepository,
    child_id: UUID,
    parent_id: UUID,
    workspace_id: UUID,
    *,
    max_depth: int = 10,
) -> tuple[bool, str | None]:
    """Check if setting parent_id would create a circular dependency.

    Traverses up the parent chain from parent_id to ensure child_id
    doesn't appear in the ancestry.

    Args:
        repo: IssueRepository instance.
        child_id: Child issue UUID.
        parent_id: Proposed parent issue UUID.
        workspace_id: Workspace UUID for RLS.
        max_depth: Maximum traversal depth to prevent infinite loops.

    Returns:
        (is_circular, error_message) tuple.
    """
    if child_id == parent_id:
        return True, "Cannot set an issue as its own parent"

    current_id = parent_id
    depth = 0

    while current_id and depth < max_depth:
        parent_issue = await repo.get_by_id(current_id)
        if not parent_issue:
            break

        # Verify workspace ownership for RLS defense-in-depth
        if parent_issue.workspace_id != workspace_id:
            break

        if parent_issue.parent_id == child_id:
            return True, "Circular parent relationship detected"

        current_id = parent_issue.parent_id
        depth += 1

    return False, None


def create_issue_relation_tools_server(
    event_queue: asyncio.Queue[str],
    *,
    tool_context: ToolContext | None = None,
) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server with 6 issue relationship tools.

    Tools included:
    - IS-005: link_issue_to_note - Link issue to note block
    - IS-006: unlink_issue_from_note - Remove issue-note link
    - IS-007: link_issues - Create issue-to-issue relationship
    - IS-008: unlink_issues - Remove issue-to-issue link
    - IS-009: add_sub_issue - Set parent-child relationship
    - IS-010: transition_issue_state - Change issue state

    Each tool handler either:
    - Returns operation payload for mutations
    - Pushes SSE approval_request events for destructive operations

    Args:
        event_queue: Queue for SSE events consumed by the stream method.
        tool_context: Tool context with db_session and workspace_id.

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions.mcp_servers.
    """

    @tool(
        "link_issue_to_note",
        "Link an issue to a note block. Creates a bidirectional relationship. "
        "Returns operation payload for approval.",
        {
            "type": "object",
            "properties": {
                "issue_id": {
                    "type": "string",
                    "description": "Issue UUID or identifier (required)",
                },
                "note_id": {
                    "type": "string",
                    "description": "Note UUID (required)",
                },
                "link_type": {
                    "type": "string",
                    "enum": ["extracted", "referenced", "related", "inline"],
                    "default": "referenced",
                    "description": "Type of link relationship",
                },
                "block_id": {
                    "type": "string",
                    "description": "TipTap block ID where link originates",
                },
            },
            "required": ["issue_id", "note_id"],
        },
    )
    async def link_issue_to_note(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: Tool context not available")

        # Resolve issue_id
        issue_uuid, error = await resolve_entity_id(
            "issue",
            args["issue_id"],
            tool_context,
        )
        if error:
            return _text_result(f"Error: {error}")

        # Resolve note_id
        note_uuid, error = await resolve_entity_id(
            "note",
            args["note_id"],
            tool_context,
        )
        if error:
            return _text_result(f"Error: {error}")

        # Verify workspace ownership
        repo = IssueRepository(tool_context.db_session)
        ws_err = await _verify_issue_workspace(repo, issue_uuid, tool_context.workspace_id)  # type: ignore[arg-type]
        if ws_err:
            return _text_result(f"Error: {ws_err}")
        ws_err = await _verify_note_workspace(note_uuid, tool_context)  # type: ignore[arg-type]
        if ws_err:
            return _text_result(f"Error: {ws_err}")

        # Build operation payload
        payload = {
            "issue_id": str(issue_uuid),
            "note_id": str(note_uuid),
            "link_type": args.get("link_type", "referenced"),
            "workspace_id": tool_context.workspace_id,
        }

        if args.get("block_id"):
            payload["block_id"] = args["block_id"]

        approval_level = get_tool_approval_level("link_issue_to_note")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"

        logger.info(
            "[IssueRelationTools] link_issue_to_note: %s → %s",
            args["issue_id"],
            args["note_id"],
        )
        return _operation_payload(
            "link_issue_to_note",
            payload,
            status=status,
            preview={
                "issue_id": args["issue_id"],
                "note_id": args["note_id"],
                "link_type": args.get("link_type", "referenced"),
            },
        )

    @tool(
        "unlink_issue_from_note",
        "Remove the link between an issue and a note. "
        "Always requires approval (destructive operation).",
        {
            "type": "object",
            "properties": {
                "issue_id": {
                    "type": "string",
                    "description": "Issue UUID or identifier (required)",
                },
                "note_id": {
                    "type": "string",
                    "description": "Note UUID (required)",
                },
            },
            "required": ["issue_id", "note_id"],
        },
    )
    async def unlink_issue_from_note(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: Tool context not available")

        # Resolve issue_id
        issue_uuid, error = await resolve_entity_id(
            "issue",
            args["issue_id"],
            tool_context,
        )
        if error:
            return _text_result(f"Error: {error}")

        # Resolve note_id
        note_uuid, error = await resolve_entity_id(
            "note",
            args["note_id"],
            tool_context,
        )
        if error:
            return _text_result(f"Error: {error}")

        # Verify workspace ownership
        repo = IssueRepository(tool_context.db_session)
        ws_err = await _verify_issue_workspace(repo, issue_uuid, tool_context.workspace_id)  # type: ignore[arg-type]
        if ws_err:
            return _text_result(f"Error: {ws_err}")
        ws_err = await _verify_note_workspace(note_uuid, tool_context)  # type: ignore[arg-type]
        if ws_err:
            return _text_result(f"Error: {ws_err}")

        logger.info(
            "[IssueRelationTools] unlink_issue_from_note: %s ← %s (approval required)",
            args["issue_id"],
            args["note_id"],
        )
        return _operation_payload(
            "unlink_issue_from_note",
            {
                "issue_id": str(issue_uuid),
                "note_id": str(note_uuid),
                "workspace_id": tool_context.workspace_id,
            },
            status="approval_required",
            preview={"issue_id": args["issue_id"], "note_id": args["note_id"]},
        )

    @tool(
        "link_issues",
        "Create a relationship link between two issues. "
        "Supports blocks, blocked_by, duplicates, and related types. "
        "Returns operation payload for approval.",
        {
            "type": "object",
            "properties": {
                "source_issue_id": {
                    "type": "string",
                    "description": "Source issue UUID or identifier (required)",
                },
                "target_issue_id": {
                    "type": "string",
                    "description": "Target issue UUID or identifier (required)",
                },
                "link_type": {
                    "type": "string",
                    "enum": ["blocks", "blocked_by", "duplicates", "related"],
                    "description": "Type of relationship (required)",
                },
            },
            "required": ["source_issue_id", "target_issue_id", "link_type"],
        },
    )
    async def link_issues(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: Tool context not available")

        # Resolve both issue IDs
        resolved: dict[str, Any] = {}
        for key in ["source_issue_id", "target_issue_id"]:
            uid, error = await resolve_entity_id("issue", args[key], tool_context)
            if error:
                return _text_result(f"Error resolving {key}: {error}")
            resolved[key] = uid
        source_uuid, target_uuid = resolved["source_issue_id"], resolved["target_issue_id"]

        # Verify workspace ownership before revealing validation details
        repo = IssueRepository(tool_context.db_session)
        for uid in [source_uuid, target_uuid]:
            ws_err = await _verify_issue_workspace(repo, uid, tool_context.workspace_id)  # type: ignore[arg-type]
            if ws_err:
                return _text_result(f"Error: {ws_err}")

        # Validate link_type and self-link
        try:
            link_type = IssueLinkType(args["link_type"])
        except ValueError:
            return _text_result(
                f"Invalid link_type: {args['link_type']}. "
                "Must be blocks, blocked_by, duplicates, or related"
            )
        if source_uuid == target_uuid:
            return _text_result("Cannot link an issue to itself")

        # Build operation payload
        payload = {
            "source_issue_id": str(source_uuid),
            "target_issue_id": str(target_uuid),
            "link_type": link_type.value,
            "workspace_id": tool_context.workspace_id,
        }

        # For blocks/blocked_by, note that inverse link will be created automatically
        preview = {
            "source_issue_id": args["source_issue_id"],
            "target_issue_id": args["target_issue_id"],
            "link_type": link_type.value,
        }

        if link_type in (IssueLinkType.BLOCKS, IssueLinkType.BLOCKED_BY):
            preview["note"] = "Inverse link will be created automatically"

        approval_level = get_tool_approval_level("link_issues")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"

        logger.info(
            "[IssueRelationTools] link_issues: %s %s %s",
            args["source_issue_id"],
            link_type.value,
            args["target_issue_id"],
        )
        return _operation_payload(
            "link_issues",
            payload,
            status=status,
            preview=preview,
        )

    @tool(
        "unlink_issues",
        "Remove a relationship link between two issues. "
        "Always requires approval (destructive operation).",
        {
            "type": "object",
            "properties": {
                "source_issue_id": {
                    "type": "string",
                    "description": "Source issue UUID or identifier (required)",
                },
                "target_issue_id": {
                    "type": "string",
                    "description": "Target issue UUID or identifier (required)",
                },
            },
            "required": ["source_issue_id", "target_issue_id"],
        },
    )
    async def unlink_issues(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: Tool context not available")

        # Resolve source_issue_id
        source_uuid, error = await resolve_entity_id(
            "issue",
            args["source_issue_id"],
            tool_context,
        )
        if error:
            return _text_result(f"Error resolving source issue: {error}")

        # Resolve target_issue_id
        target_uuid, error = await resolve_entity_id(
            "issue",
            args["target_issue_id"],
            tool_context,
        )
        if error:
            return _text_result(f"Error resolving target issue: {error}")

        # Verify workspace ownership
        repo = IssueRepository(tool_context.db_session)
        for uid in [source_uuid, target_uuid]:
            ws_err = await _verify_issue_workspace(repo, uid, tool_context.workspace_id)  # type: ignore[arg-type]
            if ws_err:
                return _text_result(f"Error: {ws_err}")

        logger.info(
            "[IssueRelationTools] unlink_issues: %s ← → %s (approval required)",
            args["source_issue_id"],
            args["target_issue_id"],
        )
        return _operation_payload(
            "unlink_issues",
            {
                "source_issue_id": str(source_uuid),
                "target_issue_id": str(target_uuid),
                "workspace_id": tool_context.workspace_id,
            },
            status="approval_required",
            preview={
                "source_issue_id": args["source_issue_id"],
                "target_issue_id": args["target_issue_id"],
            },
        )

    @tool(
        "add_sub_issue",
        "Set a parent-child relationship between issues. "
        "Child issue must not create a circular dependency. "
        "Returns operation payload for approval.",
        {
            "type": "object",
            "properties": {
                "parent_issue_id": {
                    "type": "string",
                    "description": "Parent issue UUID or identifier (required)",
                },
                "child_issue_id": {
                    "type": "string",
                    "description": "Child issue UUID or identifier (required)",
                },
            },
            "required": ["parent_issue_id", "child_issue_id"],
        },
    )
    async def add_sub_issue(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: Tool context not available")

        # Resolve parent_issue_id
        parent_uuid, error = await resolve_entity_id(
            "issue",
            args["parent_issue_id"],
            tool_context,
        )
        if error:
            return _text_result(f"Error resolving parent issue: {error}")

        # Resolve child_issue_id
        child_uuid, error = await resolve_entity_id(
            "issue",
            args["child_issue_id"],
            tool_context,
        )
        if error:
            return _text_result(f"Error resolving child issue: {error}")

        # Verify workspace ownership
        repo = IssueRepository(tool_context.db_session)
        for uid in [parent_uuid, child_uuid]:
            ws_err = await _verify_issue_workspace(repo, uid, tool_context.workspace_id)  # type: ignore[arg-type]
            if ws_err:
                return _text_result(f"Error: {ws_err}")

        # Check for circular dependency (traverse up to depth=3)
        is_circular, circular_error = await _check_circular_parent(
            repo,
            child_uuid,  # type: ignore[arg-type]
            parent_uuid,  # type: ignore[arg-type]
            UUID(tool_context.workspace_id),
        )

        if is_circular:
            return _text_result(f"Error: {circular_error}")

        # Build operation payload
        payload = {
            "parent_issue_id": str(parent_uuid),
            "child_issue_id": str(child_uuid),
            "workspace_id": tool_context.workspace_id,
        }

        approval_level = get_tool_approval_level("add_sub_issue")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"

        logger.info(
            "[IssueRelationTools] add_sub_issue: %s ← %s",
            args["parent_issue_id"],
            args["child_issue_id"],
        )
        return _operation_payload(
            "add_sub_issue",
            payload,
            status=status,
            preview={
                "parent_issue_id": args["parent_issue_id"],
                "child_issue_id": args["child_issue_id"],
            },
        )

    @tool(
        "transition_issue_state",
        "Transition an issue to a different state. "
        "Validates state belongs to the same project. "
        "Returns operation payload for approval.",
        {
            "type": "object",
            "properties": {
                "issue_id": {
                    "type": "string",
                    "description": "Issue UUID or identifier (required)",
                },
                "target_state_id": {
                    "type": "string",
                    "description": "Target state UUID (required)",
                },
                "comment": {
                    "type": "string",
                    "description": "Optional comment explaining the transition",
                },
            },
            "required": ["issue_id", "target_state_id"],
        },
    )
    async def transition_issue_state(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: Tool context not available")

        # Resolve issue_id
        issue_uuid, error = await resolve_entity_id(
            "issue",
            args["issue_id"],
            tool_context,
        )
        if error:
            return _text_result(f"Error: {error}")

        # Verify workspace ownership
        repo = IssueRepository(tool_context.db_session)
        ws_err = await _verify_issue_workspace(repo, issue_uuid, tool_context.workspace_id)  # type: ignore[arg-type]
        if ws_err:
            return _text_result(f"Error: {ws_err}")

        # Build operation payload
        payload = {
            "issue_id": str(issue_uuid),
            "target_state_id": args["target_state_id"],
            "workspace_id": tool_context.workspace_id,
        }

        if args.get("comment"):
            payload["comment"] = args["comment"]

        approval_level = get_tool_approval_level("transition_issue_state")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"

        logger.info(
            "[IssueRelationTools] transition_issue_state: %s → state %s",
            args["issue_id"],
            args["target_state_id"],
        )
        return _operation_payload(
            "transition_issue_state",
            payload,
            status=status,
            preview={
                "issue_id": args["issue_id"],
                "target_state_id": args["target_state_id"],
                "comment": args.get("comment"),
            },
        )

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            link_issue_to_note,
            unlink_issue_from_note,
            link_issues,
            unlink_issues,
            add_sub_issue,
            transition_issue_state,
        ],
    )
