"""In-process SDK custom tools for PilotSpace project operations.

Creates an SDK MCP server using create_sdk_mcp_server() with 5 project tools.
Tool handlers push content_update SSE events to a shared asyncio.Queue
that the PilotSpaceAgent stream method interleaves with SDK messages.

All project identifiers go through resolve_entity_id() for UUID/identifier resolution.
Project mutations return operation payloads for approval flow.

Architecture:
  ClaudeSDKClient (in-process) → tool handler → pushes to event_queue
  PilotSpaceAgent._stream_with_space() → reads from event_queue + SDK messages
  Frontend useContentUpdates hook → Project updates + API calls

Reference: spec 010-enhanced-mcp-tools Phase 4 (PR-001 to PR-005)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.ai.tools.entity_resolver import resolve_entity_id
from pilot_space.ai.tools.mcp_server import ToolContext, get_tool_approval_level

logger = logging.getLogger(__name__)

# MCP server name — used in allowed_tools as mcp__pilot-projects__{tool_name}
SERVER_NAME = "pilot-projects"

# All tool names for allowed_tools configuration
TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__get_project",
    f"mcp__{SERVER_NAME}__search_projects",
    f"mcp__{SERVER_NAME}__create_project",
    f"mcp__{SERVER_NAME}__update_project",
    f"mcp__{SERVER_NAME}__update_project_settings",
]

# Project identifier validation (2-10 uppercase letters)
_IDENTIFIER_PATTERN = re.compile(r"^[A-Z]{2,10}$")


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format an SSE event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _text_result(text: str) -> dict[str, Any]:
    """Create a standard MCP tool text result."""
    return {"content": [{"type": "text", "text": text}]}


def create_project_tools_server(
    event_queue: asyncio.Queue[str],
    *,
    tool_context: ToolContext | None = None,
) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server with 5 project tools.

    Each tool handler pushes content_update SSE events to event_queue
    and returns a success message for the model to continue with.

    Args:
        event_queue: Queue for SSE events consumed by the stream method.
        tool_context: ToolContext for database access and RLS enforcement.

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions.mcp_servers.
    """
    if not tool_context:
        msg = "ToolContext is required for project tools"
        raise ValueError(msg)

    @tool(
        "get_project",
        "Get project details by UUID or identifier (e.g., 'PILOT'). "
        "Optionally include issue statistics and recent issues.",
        {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID or identifier (e.g., PILOT)",
                },
                "include_stats": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include issue counts by state",
                },
                "include_recent_issues": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include 10 most recent issues",
                },
            },
            "required": ["project_id"],
        },
    )
    async def get_project(args: dict[str, Any]) -> dict[str, Any]:
        """Get project details with optional stats and recent issues."""
        from sqlalchemy import func, select

        from pilot_space.infrastructure.database.models.issue import Issue
        from pilot_space.infrastructure.database.models.state import State
        from pilot_space.infrastructure.database.repositories.project_repository import (
            ProjectRepository,
        )

        project_id_input = args.get("project_id", "")
        include_stats = args.get("include_stats", False)
        include_recent = args.get("include_recent_issues", False)

        # Resolve project ID
        project_uuid, error = await resolve_entity_id(
            "project",
            project_id_input,
            tool_context,
        )
        if error or not project_uuid:
            return _text_result(f"Error: {error or 'Invalid project ID'}")

        repo = ProjectRepository(tool_context.db_session)
        project = await repo.get_with_states(project_uuid)

        if not project or str(project.workspace_id) != tool_context.workspace_id:
            return _text_result(f"Project '{project_id_input}' not found")

        # Build project data
        project_data: dict[str, Any] = {
            "id": str(project.id),
            "name": project.name,
            "identifier": project.identifier,
            "description": project.description or "",
            "icon": project.icon,
            "lead_id": str(project.lead_id) if project.lead_id else None,
            "created_at": project.created_at.isoformat(),
            "states": [
                {
                    "id": str(state.id),
                    "name": state.name,
                    "color": state.color,
                    "group": state.group.value,
                    "sequence": state.sequence,
                }
                for state in sorted(project.states, key=lambda s: s.sequence)
            ],
        }

        # Include stats if requested
        if include_stats:
            from uuid import UUID

            workspace_id = UUID(tool_context.workspace_id)
            stats_query = (
                select(State.name, func.count(Issue.id).label("count"))
                .join(Issue, Issue.state_id == State.id)
                .where(
                    State.project_id == project.id,
                    Issue.workspace_id == workspace_id,
                    Issue.is_deleted == False,  # noqa: E712
                )
                .group_by(State.name)
            )
            stats_result = await tool_context.db_session.execute(stats_query)
            issue_stats: dict[str, int] = {row.name: row.count for row in stats_result}  # type: ignore[attr-defined]
            project_data["issue_stats"] = issue_stats

        # Include recent issues if requested
        if include_recent:
            from uuid import UUID

            workspace_id = UUID(tool_context.workspace_id)
            recent_query = (
                select(Issue)
                .where(
                    Issue.project_id == project.id,
                    Issue.workspace_id == workspace_id,
                    Issue.is_deleted == False,  # noqa: E712
                )
                .order_by(Issue.created_at.desc())
                .limit(10)
            )
            recent_result = await tool_context.db_session.execute(recent_query)
            recent_issues = recent_result.scalars().all()
            recent_list: list[dict[str, Any]] = [
                {
                    "id": str(issue.id),
                    "identifier": f"{project.identifier}-{issue.sequence_id}",
                    "title": issue.name,
                    "priority": issue.priority.value if issue.priority else None,
                }
                for issue in recent_issues
            ]
            project_data["recent_issues"] = recent_list

        logger.info("[ProjectTools] get_project: %s", project.identifier)
        return _text_result(
            f"Project '{project.identifier}' retrieved successfully.\n\n"
            f"Details: {json.dumps(project_data, indent=2)}"
        )

    @tool(
        "search_projects",
        "Search projects by name or identifier in the workspace. "
        "Returns matching projects with basic details.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term for name or identifier",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum results (max: 100)",
                },
            },
            "required": ["query"],
        },
    )
    async def search_projects(args: dict[str, Any]) -> dict[str, Any]:
        """Search projects in workspace."""
        from pilot_space.infrastructure.database.repositories.project_repository import (
            ProjectRepository,
        )

        query = args.get("query", "").strip()
        limit = min(args.get("limit", 20), 100)

        if not query:
            return _text_result("Error: Search query cannot be empty")

        repo = ProjectRepository(tool_context.db_session)
        workspace_uuid = tool_context.workspace_id

        try:
            from uuid import UUID

            workspace_id = UUID(workspace_uuid)
        except (ValueError, AttributeError):
            return _text_result("Error: Invalid workspace ID")

        projects = await repo.search_projects(
            workspace_id=workspace_id,
            search_term=query,
            limit=limit,
        )

        if not projects:
            return _text_result(f"No projects found matching '{query}'")

        results = [
            {
                "id": str(p.id),
                "identifier": p.identifier,
                "name": p.name,
                "description": (p.description or "")[:100],
                "icon": p.icon,
            }
            for p in projects
        ]

        logger.info("[ProjectTools] search_projects: query='%s' found=%d", query, len(results))
        return _text_result(
            f"Found {len(results)} project(s) matching '{query}':\n\n"
            f"{json.dumps(results, indent=2)}"
        )

    @tool(
        "create_project",
        "Create a new project in the workspace. "
        "Requires approval. Default states will be created automatically.",
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project display name",
                },
                "identifier": {
                    "type": "string",
                    "description": "2-10 uppercase letters (e.g., PILOT)",
                },
                "description": {
                    "type": "string",
                    "description": "Optional project description",
                },
                "lead_id": {
                    "type": "string",
                    "description": "Optional user UUID for project lead",
                },
                "icon": {
                    "type": "string",
                    "description": "Optional emoji or icon identifier",
                },
            },
            "required": ["name", "identifier"],
        },
    )
    async def create_project(args: dict[str, Any]) -> dict[str, Any]:
        """Create new project (requires approval)."""
        from pilot_space.infrastructure.database.models.state import DEFAULT_STATES
        from pilot_space.infrastructure.database.repositories.project_repository import (
            ProjectRepository,
        )

        name = args.get("name", "").strip()
        identifier = args.get("identifier", "").strip().upper()
        description = args.get("description", "").strip()
        lead_id = args.get("lead_id")
        icon = args.get("icon")

        # Validate name
        if not name:
            return _text_result("Error: Project name is required")

        # Validate identifier format
        if not _IDENTIFIER_PATTERN.match(identifier):
            return _text_result(
                f"Error: Identifier '{identifier}' is invalid. "
                "Must be 2-10 uppercase letters (e.g., PILOT, PROJ)"
            )

        # Check for duplicate identifier
        repo = ProjectRepository(tool_context.db_session)
        try:
            from uuid import UUID

            workspace_id = UUID(tool_context.workspace_id)
        except (ValueError, AttributeError):
            return _text_result("Error: Invalid workspace ID")

        exists = await repo.identifier_exists(workspace_id, identifier)
        if exists:
            return _text_result(
                f"Error: Project identifier '{identifier}' already exists in this workspace"
            )

        # Build approval payload
        approval_level = get_tool_approval_level("create_project")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"
        event_data = {
            "operation": "create_project",
            "status": status,
            "approval_level": approval_level.value,
            "project_data": {
                "name": name,
                "identifier": identifier,
                "description": description or None,
                "lead_id": lead_id,
                "icon": icon,
                "workspace_id": str(workspace_id),
            },
            "default_states": [
                {
                    "name": str(state["name"]),
                    "color": str(state["color"]),
                    "group": state["group"].value,  # type: ignore[union-attr]
                    "sequence": int(state["sequence"]),  # type: ignore[arg-type]
                }
                for state in DEFAULT_STATES
            ],
        }

        await event_queue.put(_sse_event("approval_request", event_data))
        logger.info("[ProjectTools] create_project: %s (approval required)", identifier)
        return _text_result(
            f"Project '{identifier}' creation requested. "
            f"Approval required. Default states will be created:\n"
            f"{json.dumps([s['name'] for s in DEFAULT_STATES], indent=2)}"
        )

    @tool(
        "update_project",
        "Update project details. Identifier is immutable. Requires approval for changes.",
        {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID or identifier of project",
                },
                "name": {
                    "type": "string",
                    "description": "New project name",
                },
                "description": {
                    "type": "string",
                    "description": "New description",
                },
                "lead_id": {
                    "type": "string",
                    "description": "New lead user UUID",
                },
                "icon": {
                    "type": "string",
                    "description": "New icon",
                },
            },
            "required": ["project_id"],
        },
    )
    async def update_project(args: dict[str, Any]) -> dict[str, Any]:
        """Update project details (requires approval)."""
        from pilot_space.infrastructure.database.repositories.project_repository import (
            ProjectRepository,
        )

        project_id_input = args.get("project_id", "")
        name = args.get("name")
        description = args.get("description")
        lead_id = args.get("lead_id")
        icon = args.get("icon")

        # Check if identifier was provided (immutable)
        if "identifier" in args:
            return _text_result(
                "Error: Project identifier is immutable and cannot be changed. "
                "Only name, description, lead_id, and icon can be updated."
            )

        # Resolve project ID
        project_uuid, error = await resolve_entity_id(
            "project",
            project_id_input,
            tool_context,
        )
        if error or not project_uuid:
            return _text_result(f"Error: {error or 'Invalid project ID'}")

        repo = ProjectRepository(tool_context.db_session)
        project = await repo.get_by_id(project_uuid)

        if not project or str(project.workspace_id) != tool_context.workspace_id:
            return _text_result(f"Project '{project_id_input}' not found")

        # Build change diff
        changes = {}
        if name and name != project.name:
            changes["name"] = {"old": project.name, "new": name}
        if description is not None and description != (project.description or ""):
            changes["description"] = {"old": project.description or "", "new": description}
        if lead_id and str(project.lead_id) != lead_id:
            changes["lead_id"] = {
                "old": str(project.lead_id) if project.lead_id else None,
                "new": lead_id,
            }
        if icon and icon != project.icon:
            changes["icon"] = {"old": project.icon, "new": icon}

        if not changes:
            return _text_result("No changes detected. Provide at least one field to update.")

        # Build approval payload
        approval_level = get_tool_approval_level("update_project")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"
        event_data = {
            "operation": "update_project",
            "status": status,
            "approval_level": approval_level.value,
            "project_id": str(project.id),
            "identifier": project.identifier,
            "changes": changes,
            "updated_fields": {
                "name": name,
                "description": description,
                "lead_id": lead_id,
                "icon": icon,
            },
        }

        await event_queue.put(_sse_event("approval_request", event_data))
        logger.info("[ProjectTools] update_project: %s (approval required)", project.identifier)
        return _text_result(
            f"Project '{project.identifier}' update requested. "
            f"Approval required for changes:\n{json.dumps(changes, indent=2)}"
        )

    @tool(
        "update_project_settings",
        "Update project settings (JSONB merge). "
        "New settings are merged with existing. Requires approval.",
        {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID or identifier of project",
                },
                "settings": {
                    "type": "object",
                    "description": "Settings to merge (JSONB)",
                },
            },
            "required": ["project_id", "settings"],
        },
    )
    async def update_project_settings(args: dict[str, Any]) -> dict[str, Any]:
        """Update project settings (requires approval)."""
        from pilot_space.infrastructure.database.repositories.project_repository import (
            ProjectRepository,
        )

        project_id_input = args.get("project_id", "")
        new_settings = args.get("settings", {})

        if not isinstance(new_settings, dict):
            return _text_result("Error: Settings must be a JSON object")

        if not new_settings:
            return _text_result("Error: Settings cannot be empty")

        # Resolve project ID
        project_uuid, error = await resolve_entity_id(
            "project",
            project_id_input,
            tool_context,
        )
        if error or not project_uuid:
            return _text_result(f"Error: {error or 'Invalid project ID'}")

        repo = ProjectRepository(tool_context.db_session)
        project = await repo.get_by_id(project_uuid)

        if not project or str(project.workspace_id) != tool_context.workspace_id:
            return _text_result(f"Project '{project_id_input}' not found")

        existing_settings = project.settings or {}
        merged_settings = {**existing_settings, **new_settings}

        # Build approval payload
        approval_level = get_tool_approval_level("update_project_settings")
        status = "approval_required" if approval_level.value != "auto_execute" else "pending_apply"
        event_data = {
            "operation": "update_project_settings",
            "status": status,
            "approval_level": approval_level.value,
            "project_id": str(project.id),
            "identifier": project.identifier,
            "settings_before": existing_settings,
            "settings_after": merged_settings,
            "settings_diff": new_settings,
        }

        await event_queue.put(_sse_event("approval_request", event_data))
        logger.info(
            "[ProjectTools] update_project_settings: %s (approval required)",
            project.identifier,
        )
        return _text_result(
            f"Project '{project.identifier}' settings update requested. "
            f"Approval required.\n\nBefore: {json.dumps(existing_settings, indent=2)}\n\n"
            f"After: {json.dumps(merged_settings, indent=2)}"
        )

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            get_project,
            search_projects,
            create_project,
            update_project,
            update_project_settings,
        ],
    )
