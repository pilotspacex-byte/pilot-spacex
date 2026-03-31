"""In-process SDK MCP server for note query/search operations.

Extracted from note_server.py to maintain file size compliance (<700 lines).
Contains read-only search tools that do not emit SSE events.

Reference: spec 010-enhanced-mcp-tools CQRS-lite split
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.tools.mcp_server import ToolContext

logger = get_logger(__name__)

# MCP server name — used in allowed_tools as mcp__pilot-notes-query__{tool_name}
SERVER_NAME = "pilot-notes-query"

# All tool names for allowed_tools configuration
TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__search_notes",
]


def create_note_query_server(
    *,
    tool_context: ToolContext | None = None,
) -> McpSdkServerConfig:
    """Create SDK MCP server with note query/search tools.

    Args:
        tool_context: ToolContext for DB access and RLS enforcement.
    """

    def _text_result(text: str) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": text}]}

    @tool(
        "search_notes",
        "Search for notes by title in the workspace. Returns matching notes with metadata.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for note title",
                },
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
            # Explicit project_id → active_project_id context fallback (T043)
            project_id_str = args.get("project_id") or tool_context.extra.get("active_project_id")
            project_id = UUID(project_id_str) if project_id_str else None
            limit = min(args.get("limit", 20), 100)
            include_content = args.get("include_content", False)

            repo = NoteRepository(tool_context.db_session)
            notes = await repo.list_notes(
                workspace_id,
                project_ids=[project_id] if project_id else None,
                search=query,
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

            logger.info(
                "mcp_tool_invoked",
                tool="search_notes",
                query=query[:50],
                found=len(results),
            )
            return _text_result(
                json.dumps(
                    {
                        "count": len(results),
                        "query": query,
                        "notes": [
                            {
                                "id": r["id"],
                                "title": r["title"],
                                "projectId": r.get("project_id"),
                                "preview": r.get("content_preview", ""),
                                "createdAt": r.get("created_at", ""),
                            }
                            for r in results
                        ],
                    }
                )
            )
        except Exception as e:
            logger.exception("mcp_tool_error", tool="search_notes")
            return _text_result(f"Error searching notes: {e!s}")

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[search_notes],
    )
