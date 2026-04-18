"""In-process SDK MCP server for workspace memory recall.

Provides a ``recall_memory`` tool that wraps ``MemoryRecallService`` for
on-demand context retrieval. Part of the lazy-context architecture
(Phase 81): the agent calls this tool when it needs historical context
instead of receiving pre-loaded memory blocks in the system prompt.

Reference: Phase 81 — Lazy Context & Demand-Driven Memory
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.tools.mcp_server import ToolContext

logger = get_logger(__name__)

# MCP server name — used in allowed_tools as mcp__pilot-memory__{tool_name}
SERVER_NAME = "pilot-memory"

# All tool names for allowed_tools configuration
TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__recall_memory",
]


def create_memory_server(
    *,
    tool_context: ToolContext | None = None,
) -> McpSdkServerConfig:
    """Create SDK MCP server with the recall_memory tool.

    Args:
        tool_context: ToolContext for workspace isolation and DB access.
    """

    def _text_result(text: str) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": text}]}

    @tool(
        "recall_memory",
        "Search workspace memories (past decisions, corrections, review findings, "
        "agent turns). Returns matching memories ranked by relevance.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query to search memories",
                },
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "description": "Max results (1-10)",
                },
                "types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "note_summary",
                            "issue_decision",
                            "agent_turn",
                            "user_correction",
                            "pr_review_finding",
                        ],
                    },
                    "description": "Filter by memory types (omit for all)",
                },
            },
            "required": ["query"],
        },
    )
    async def recall_memory(args: dict[str, Any]) -> dict[str, Any]:
        if not tool_context:
            return _text_result("Error: tool_context not available for recall_memory")

        from uuid import UUID

        from pilot_space.application.services.memory.memory_recall_service import (
            RecallPayload,
        )

        try:
            # Resolve MemoryRecallService from DI container (same pattern as
            # pilotspace_agent.py lines 996-1005).
            try:
                from pilot_space.container.container import get_container

                memory_recall_service = get_container().memory_recall_service()
            except Exception:
                logger.debug("Could not resolve MemoryRecallService", exc_info=True)
                return _text_result(
                    "Error: MemoryRecallService not available. "
                    "Memory recall requires the knowledge graph to be configured."
                )

            query = args["query"]
            limit = min(args.get("limit", 5), 10)
            types_raw = args.get("types")
            types_tuple = tuple(types_raw) if types_raw else None

            payload = RecallPayload(
                workspace_id=UUID(tool_context.workspace_id),
                query=query,
                k=limit,
                types=types_tuple,
                user_id=UUID(tool_context.user_id) if tool_context.user_id else None,
            )

            recall_result = await memory_recall_service.recall(payload)
            items = recall_result.items

            logger.info(
                "mcp_tool_invoked",
                tool="recall_memory",
                query=query[:50],
                found=len(items),
            )

            return _text_result(
                json.dumps(
                    {
                        "count": len(items),
                        "query": query,
                        "cache_hit": recall_result.cache_hit,
                        "elapsed_ms": recall_result.elapsed_ms,
                        "memories": [
                            {
                                "source_type": item.source_type,
                                "source_id": str(item.source_id),
                                "score": round(item.score, 3),
                                "snippet": item.snippet,
                                "created_at": item.created_at if item.created_at else None,
                            }
                            for item in items
                        ],
                    }
                )
            )
        except Exception as e:
            logger.exception("mcp_tool_error", tool="recall_memory")
            return _text_result(f"Error recalling memories: {e!s}")

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[recall_memory],
    )
