"""In-process SDK custom tools for PilotSpace issue CRUD operations.

Creates an SDK MCP server with 4 issue CRUD tools (IS-001 to IS-004).
Tool handlers push SSE events to a shared asyncio.Queue that the PilotSpaceAgent
stream method interleaves with SDK messages.

For issue relationship tools (IS-005 to IS-010), see issue_relation_server.py.

Architecture:
  ClaudeSDKClient (in-process) → tool handler → pushes to event_queue
  PilotSpaceAgent._stream_with_space() → reads from event_queue + SDK messages
  Frontend stores → issue updates + API calls

Reference: spec 010-enhanced-mcp-tools Phase 3 (T010-T012)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.ai.tools.entity_resolver import (
    EntityResolutionError,
    resolve_entity_id_strict,
)
from pilot_space.ai.tools.mcp_server import ToolContext, get_tool_approval_level

if TYPE_CHECKING:
    from pilot_space.ai.mcp.event_publisher import EventPublisher
from pilot_space.infrastructure.database.repositories.issue_link_repository import (
    IssueLinkRepository,
)
from pilot_space.infrastructure.database.repositories.issue_repository import (
    IssueFilters,
    IssueRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# MCP server name — used in allowed_tools as mcp__pilot-issues__{tool_name}
SERVER_NAME = "pilot-issues"

# Tool names for CRUD operations
TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__get_issue",
    f"mcp__{SERVER_NAME}__search_issues",
    f"mcp__{SERVER_NAME}__create_issue",
    f"mcp__{SERVER_NAME}__update_issue",
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
    """Create a standard operation payload for approval/execution.

    Args:
        operation: Operation name (e.g., "create_issue", "update_issue").
        payload: Operation data.
        status: "pending_apply" or "approval_required".
        preview: Optional preview data for frontend display.

    Returns:
        Operation payload dict.
    """
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


def create_issue_tools_server(
    publisher: EventPublisher,
    *,
    tool_context: ToolContext | None = None,
) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server with 4 issue CRUD tools.

    Tools included:
    - IS-001: get_issue - Get full issue details with relations
    - IS-002: search_issues - Search issues with filters
    - IS-003: create_issue - Create new issue
    - IS-004: update_issue - Update existing issue

    Each tool handler either:
    - Returns data directly for read operations (get_issue, search_issues)
    - Returns operation payload for mutations (create, update)

    Args:
        event_queue: Queue for SSE events consumed by the stream method.
        tool_context: Tool context with db_session and workspace_id.

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions.mcp_servers.
    """

    @tool(
        "get_issue",
        "Get full details of a specific issue including relationships. "
        "Use issue UUID or identifier like PILOT-123.",
        {
            "type": "object",
            "properties": {
                "issue_id": {
                    "type": "string",
                    "description": "Issue UUID or identifier (e.g., PILOT-123)",
                },
                "include_notes": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include linked notes",
                },
                "include_sub_issues": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include sub-issues",
                },
                "include_links": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include issue links (blocks, duplicates, etc.)",
                },
                "include_activity": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include activity history",
                },
                "include_ai_context": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include AI context aggregation",
                },
            },
            "required": ["issue_id"],
        },
    )
    async def get_issue(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: Tool context not available")

        # Resolve entity ID (UUID or identifier like PILOT-123)
        try:
            issue_uuid = await resolve_entity_id_strict("issue", args["issue_id"], tool_context)
        except EntityResolutionError as e:
            return _text_result(f"Error: {e}")

        # Get issue with relations
        repo = IssueRepository(tool_context.db_session)
        issue = await repo.get_by_id_with_relations(issue_uuid)

        if not issue or str(issue.workspace_id) != tool_context.workspace_id:
            return _text_result(f"Issue {args['issue_id']} not found")

        # Build response dict
        result: dict[str, Any] = {
            "id": str(issue.id),
            "identifier": f"{issue.project.identifier}-{issue.sequence_id}",
            "name": issue.name,
            "description": issue.description,
            "priority": issue.priority.value,
            "state": {
                "id": str(issue.state.id),
                "name": issue.state.name,
                "group": issue.state.group.value,
            },
            "project": {
                "id": str(issue.project.id),
                "identifier": issue.project.identifier,
                "name": issue.project.name,
            },
            "assignee": (
                {
                    "id": str(issue.assignee.id),
                    "name": issue.assignee.full_name or issue.assignee.email,
                }
                if issue.assignee
                else None
            ),
            "reporter": (
                {
                    "id": str(issue.reporter.id),
                    "name": issue.reporter.full_name or issue.reporter.email,
                }
                if issue.reporter
                else None
            ),
            "estimate_points": issue.estimate_points,
            "start_date": issue.start_date.isoformat() if issue.start_date else None,
            "target_date": issue.target_date.isoformat() if issue.target_date else None,
            "created_at": issue.created_at.isoformat(),
            "updated_at": issue.updated_at.isoformat(),
        }

        # Include sub-issues if requested
        if args.get("include_sub_issues", True):
            result["sub_issues"] = [
                {
                    "id": str(sub.id),
                    "identifier": f"{issue.project.identifier}-{sub.sequence_id}",
                    "name": sub.name,
                    "state": sub.state.name if sub.state else "Unknown",
                }
                for sub in issue.sub_issues
            ]

        # Include note links if requested
        if args.get("include_notes", True):
            result["note_links"] = [
                {
                    "note_id": str(link.note_id),
                    "link_type": link.link_type.value,
                    "block_id": link.block_id,
                }
                for link in issue.note_links
            ]

        # Include issue links if requested
        if args.get("include_links", False):
            link_repo = IssueLinkRepository(tool_context.db_session)
            links = await link_repo.find_all_for_issue(
                issue.id,
                UUID(tool_context.workspace_id),
            )
            result["issue_links"] = [
                {
                    "source_id": str(link.source_issue_id),
                    "target_id": str(link.target_issue_id),
                    "link_type": link.link_type.value,
                }
                for link in links
            ]

        logger.info("[IssueTools] get_issue: %s", args["issue_id"])
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    @tool(
        "search_issues",
        "Search for issues in the workspace with filters. "
        "Returns list of matching issues with basic details.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for issue name/description",
                },
                "project_id": {
                    "type": "string",
                    "description": "Filter by project UUID or identifier",
                },
                "state_group": {
                    "type": "string",
                    "enum": ["backlog", "unstarted", "started", "completed", "cancelled"],
                    "description": "Filter by state group",
                },
                "priority": {
                    "type": "string",
                    "enum": ["none", "low", "medium", "high", "urgent"],
                    "description": "Filter by priority",
                },
                "assignee_id": {
                    "type": "string",
                    "description": "Filter by assignee UUID",
                },
                "label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by label UUIDs",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "maximum": 100,
                    "description": "Maximum results",
                },
            },
        },
    )
    async def search_issues(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: Tool context not available")

        # Build filters
        filters = IssueFilters()

        # Resolve project_id if provided
        if args.get("project_id"):
            try:
                filters.project_id = await resolve_entity_id_strict(
                    "project",
                    args["project_id"],
                    tool_context,
                )
            except EntityResolutionError as e:
                return _text_result(f"Error: {e}")

        # Apply other filters
        if args.get("state_group"):
            from pilot_space.infrastructure.database.models import StateGroup

            filters.state_groups = [StateGroup(args["state_group"])]

        if args.get("priority"):
            from pilot_space.infrastructure.database.models import IssuePriority

            filters.priorities = [IssuePriority(args["priority"])]

        if args.get("assignee_id"):
            filters.assignee_ids = [UUID(args["assignee_id"])]

        if args.get("label_ids"):
            filters.label_ids = [UUID(lid) for lid in args["label_ids"]]

        if args.get("query"):
            filters.search_term = args["query"]

        # Execute query
        repo = IssueRepository(tool_context.db_session)
        limit = min(args.get("limit", 20), 100)

        page = await repo.get_workspace_issues(
            UUID(tool_context.workspace_id),
            filters=filters,
            page_size=limit,
        )

        # Build results
        results = [
            {
                "id": str(issue.id),
                "identifier": f"{issue.project.identifier}-{issue.sequence_id}",
                "name": issue.name,
                "priority": issue.priority.value,
                "state": issue.state.name,
                "assignee": (
                    issue.assignee.full_name or issue.assignee.email
                    if issue.assignee
                    else "Unassigned"
                ),
            }
            for issue in page.items
        ]

        logger.info("[IssueTools] search_issues: %d results", len(results))
        return {"content": [{"type": "text", "text": json.dumps(results, indent=2)}]}

    @tool(
        "create_issue",
        "Create a new issue in a project. Returns operation payload for approval.",
        {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID or identifier (required)",
                },
                "title": {
                    "type": "string",
                    "description": "Issue title (required)",
                },
                "description": {
                    "type": "string",
                    "description": "Issue description (markdown)",
                },
                "priority": {
                    "type": "string",
                    "enum": ["none", "low", "medium", "high", "urgent"],
                    "default": "medium",
                },
                "state_id": {
                    "type": "string",
                    "description": "Initial state UUID (optional, defaults to project default)",
                },
                "assignee_id": {
                    "type": "string",
                    "description": "Assignee UUID (optional)",
                },
                "label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label UUIDs",
                },
                "parent_id": {
                    "type": "string",
                    "description": "Parent issue UUID for sub-tasks",
                },
                "estimate_points": {
                    "type": "integer",
                    "description": "Story points estimate",
                },
                "target_date": {
                    "type": "string",
                    "description": "Due date (ISO format: YYYY-MM-DD)",
                },
            },
            "required": ["project_id", "title", "description"],
        },
    )
    async def create_issue(args: dict[str, Any]) -> dict[str, Any]:
        logger.info("mcp_tool_invoked", tool="create_issue", title=args.get("title", "")[:80])
        if not tool_context:
            return _text_result("Error: Tool context not available")

        # Resolve project_id
        try:
            project_uuid = await resolve_entity_id_strict(
                "project", args["project_id"], tool_context
            )
        except EntityResolutionError as e:
            return _text_result(f"Error: {e}")

        # Build operation payload
        payload = {
            "project_id": str(project_uuid),
            "title": args["title"],
            "description": args.get("description", ""),
            "priority": args.get("priority", "medium"),
            "workspace_id": tool_context.workspace_id,
        }

        # Optional fields
        if args.get("state_id"):
            payload["state_id"] = args["state_id"]
        if args.get("assignee_id"):
            payload["assignee_id"] = args["assignee_id"]
        if args.get("label_ids"):
            payload["label_ids"] = args["label_ids"]
        if args.get("parent_id"):
            payload["parent_id"] = args["parent_id"]
        if args.get("estimate_points"):
            payload["estimate_points"] = args["estimate_points"]
        if args.get("target_date"):
            payload["target_date"] = args["target_date"]

        approval_level = get_tool_approval_level("create_issue")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"

        logger.info("[IssueTools] create_issue: '%s'", args["title"])
        return _operation_payload(
            "create_issue",
            payload,
            status=status,
            preview={"title": args["title"], "priority": args.get("priority", "medium")},
        )

    @tool(
        "update_issue",
        "Update an existing issue. State changes must use transition_issue_state. "
        "Returns operation payload for approval.",
        {
            "type": "object",
            "properties": {
                "issue_id": {
                    "type": "string",
                    "description": "Issue UUID or identifier (required)",
                },
                "title": {
                    "type": "string",
                    "description": "New issue title",
                },
                "description": {
                    "type": "string",
                    "description": "New issue description (markdown)",
                },
                "priority": {
                    "type": "string",
                    "enum": ["none", "low", "medium", "high", "urgent"],
                },
                "assignee_id": {
                    "type": "string",
                    "description": "New assignee UUID",
                },
                "estimate_points": {
                    "type": "integer",
                    "description": "Story points estimate",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date (ISO format: YYYY-MM-DD)",
                },
                "target_date": {
                    "type": "string",
                    "description": "Due date (ISO format: YYYY-MM-DD)",
                },
                "add_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label UUIDs to add",
                },
                "remove_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label UUIDs to remove",
                },
            },
            "required": ["issue_id"],
        },
    )
    async def update_issue(args: dict[str, Any]) -> dict[str, Any]:
        logger.info("mcp_tool_invoked", tool="update_issue", issue_id=args.get("issue_id", ""))
        if not tool_context:
            return _text_result("Error: Tool context not available")

        # Resolve issue_id
        try:
            issue_uuid = await resolve_entity_id_strict("issue", args["issue_id"], tool_context)
        except EntityResolutionError as e:
            return _text_result(f"Error: {e}")

        # Verify workspace ownership before allowing update
        repo = IssueRepository(tool_context.db_session)
        issue = await repo.get_by_id(issue_uuid)
        if not issue or str(issue.workspace_id) != tool_context.workspace_id:
            return _text_result(f"Issue {args['issue_id']} not found")

        # Build operation payload with only provided fields
        payload: dict[str, Any] = {
            "issue_id": str(issue_uuid),
        }

        # Track changes for preview
        changes = []

        if "title" in args:
            payload["title"] = args["title"]
            changes.append(f"title → '{args['title']}'")

        if "description" in args:
            payload["description"] = args["description"]
            changes.append("description updated")

        if "priority" in args:
            payload["priority"] = args["priority"]
            changes.append(f"priority → {args['priority']}")

        if "assignee_id" in args:
            payload["assignee_id"] = args["assignee_id"]
            changes.append("assignee changed")

        if "estimate_points" in args:
            payload["estimate_points"] = args["estimate_points"]
            changes.append(f"estimate → {args['estimate_points']} points")

        if "start_date" in args:
            payload["start_date"] = args["start_date"]
            changes.append(f"start date → {args['start_date']}")

        if "target_date" in args:
            payload["target_date"] = args["target_date"]
            changes.append(f"target date → {args['target_date']}")

        if "add_label_ids" in args:
            payload["add_label_ids"] = args["add_label_ids"]
            changes.append(f"adding {len(args['add_label_ids'])} labels")

        if "remove_label_ids" in args:
            payload["remove_label_ids"] = args["remove_label_ids"]
            changes.append(f"removing {len(args['remove_label_ids'])} labels")

        # PermissionCheckHook already handled the approval gate before this tool ran.
        # Apply changes directly to the DB.
        import contextlib
        from datetime import date as date_type

        from pilot_space.infrastructure.database.models.issue import IssuePriority

        if "title" in args:
            issue.name = args["title"]
        if "description" in args:
            issue.description = args["description"]
            issue.description_html = None  # Clear stale HTML so frontend falls back to markdown
        if "priority" in args:
            priority_map = {
                "urgent": IssuePriority.URGENT,
                "high": IssuePriority.HIGH,
                "medium": IssuePriority.MEDIUM,
                "low": IssuePriority.LOW,
                "none": IssuePriority.NONE,
            }
            new_priority = priority_map.get(str(args["priority"]).lower())
            if new_priority:
                issue.priority = new_priority
        if "assignee_id" in args:
            with contextlib.suppress(ValueError, TypeError):
                issue.assignee_id = UUID(args["assignee_id"]) if args["assignee_id"] else None
        if "estimate_points" in args:
            issue.estimate_points = args["estimate_points"]
        if "start_date" in args:
            with contextlib.suppress(ValueError, TypeError):
                issue.start_date = date_type.fromisoformat(args["start_date"])
        if "target_date" in args:
            with contextlib.suppress(ValueError, TypeError):
                issue.target_date = date_type.fromisoformat(args["target_date"])

        # Handle label additions/removals
        if "add_label_ids" in args or "remove_label_ids" in args:
            from sqlalchemy import delete, insert, select

            from pilot_space.infrastructure.database.models.issue_label import issue_labels

            result = await tool_context.db_session.execute(
                select(issue_labels.c.label_id).where(issue_labels.c.issue_id == issue_uuid)
            )
            current_label_ids = {row[0] for row in result.fetchall()}

            if "add_label_ids" in args:
                for lid_str in args["add_label_ids"]:
                    with contextlib.suppress(ValueError, TypeError):
                        current_label_ids.add(UUID(lid_str))
            if "remove_label_ids" in args:
                for lid_str in args["remove_label_ids"]:
                    with contextlib.suppress(ValueError, TypeError):
                        current_label_ids.discard(UUID(lid_str))

            await tool_context.db_session.execute(
                delete(issue_labels).where(issue_labels.c.issue_id == issue_uuid)
            )
            if current_label_ids:
                await tool_context.db_session.execute(
                    insert(issue_labels),
                    [{"issue_id": issue_uuid, "label_id": lid} for lid in current_label_ids],
                )

        await tool_context.db_session.flush()
        await tool_context.db_session.commit()

        # Emit issue_updated event so frontend knows to refetch the issue
        await publisher.publish_content_update(
            {
                "operation": "issue_updated",
                "issueId": str(issue_uuid),
                "noteId": "",
            }
        )

        logger.info(
            "[IssueTools] update_issue applied: %s changes=%s",
            args["issue_id"],
            changes,
        )
        return _text_result(
            f"Issue {args['issue_id']} updated: {', '.join(changes) or 'no changes'}."
        )

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            get_issue,
            search_issues,
            create_issue,
            update_issue,
        ],
    )
