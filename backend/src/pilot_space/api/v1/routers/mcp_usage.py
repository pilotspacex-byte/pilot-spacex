"""MCP tool usage analytics endpoint.

Provides invocation counts for remote MCP tools, sourced
from the immutable audit_log table (action='ai.mcp_tool_call').

Phase 34 — MCPOB-02.
"""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from pilot_space.api.middleware.request_context import WorkspaceId
from pilot_space.dependencies import CurrentUserId, DbSession
from pilot_space.infrastructure.database.models.audit_log import AuditLog
from pilot_space.infrastructure.database.models.workspace_mcp_server import WorkspaceMcpServer

router = APIRouter(prefix="/mcp-usage", tags=["MCP Usage"])


class McpToolUsageEntry(BaseModel):
    """Per-tool invocation count entry."""

    server_key: str
    server_name: str
    tool_name: str
    invocation_count: int


class McpServerSummary(BaseModel):
    """Per-server total invocation count."""

    server_key: str
    server_name: str
    total_invocations: int


class McpToolUsageResponse(BaseModel):
    """Aggregated MCP tool usage for a workspace and date period."""

    workspace_id: str
    period_start: date
    period_end: date
    by_server: list[McpServerSummary]
    by_tool: list[McpToolUsageEntry]


@router.get("", response_model=McpToolUsageResponse, summary="Get MCP tool usage")
async def get_mcp_tool_usage(
    workspace_id: WorkspaceId,
    current_user_id: CurrentUserId,
    session: DbSession,
    start_date: Annotated[date | None, Query(description="Period start date")] = None,
    end_date: Annotated[date | None, Query(description="Period end date")] = None,
) -> McpToolUsageResponse:
    """Get per-server and per-tool MCP invocation counts for the workspace.

    Queries the immutable audit_log table for rows where
    action='ai.mcp_tool_call', aggregating by server_key and tool_name.

    Default period: last 30 days.

    Args:
        workspace_id: Workspace UUID from request context header.
        current_user_id: Current authenticated user ID.
        session: Database session.
        start_date: Optional period start date (inclusive).
        end_date: Optional period end date (inclusive).

    Returns:
        Aggregated MCP tool usage with by_server and by_tool breakdowns.
    """
    if not end_date:
        end_date = datetime.now(UTC).date()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=UTC)

    # GROUP BY server_key + tool_name using portable JSONB extraction.
    # func.json_extract_path_text works with both PostgreSQL JSONB and SQLite JSON.
    server_key_col = func.json_extract_path_text(AuditLog.payload, "server_key")
    tool_name_col = func.json_extract_path_text(AuditLog.payload, "tool_name")

    stmt = (
        select(
            server_key_col.label("server_key"),
            tool_name_col.label("tool_name"),
            func.count(AuditLog.id).label("invocation_count"),
        )
        .where(
            (AuditLog.workspace_id == workspace_id)
            & (AuditLog.action == "ai.mcp_tool_call")
            & (AuditLog.created_at >= start_dt)
            & (AuditLog.created_at <= end_dt)
        )
        .group_by(server_key_col, tool_name_col)
        .order_by(func.count(AuditLog.id).desc())
    )
    rows = (await session.execute(stmt)).all()

    # Resolve display names from workspace_mcp_servers via LEFT JOIN equivalent.
    server_ids: list[uuid.UUID] = []
    for row in rows:
        if row.server_key and row.server_key.startswith("remote_"):
            with contextlib.suppress(ValueError):
                server_ids.append(uuid.UUID(row.server_key[len("remote_") :]))

    server_names: dict[str, str] = {}
    if server_ids:
        name_stmt = select(WorkspaceMcpServer.id, WorkspaceMcpServer.display_name).where(
            WorkspaceMcpServer.id.in_(server_ids)
        )
        for srv in (await session.execute(name_stmt)).all():
            server_names[f"remote_{srv.id}"] = srv.display_name

    # Build by_tool list (inherits ORDER BY count DESC from DB query)
    by_tool = [
        McpToolUsageEntry(
            server_key=row.server_key or "",
            server_name=server_names.get(row.server_key or "", row.server_key or "unknown"),
            tool_name=row.tool_name or "",
            invocation_count=row.invocation_count,
        )
        for row in rows
    ]

    # Aggregate by_server — sorted descending by total_invocations
    server_totals: dict[str, int] = {}
    for entry in by_tool:
        server_totals[entry.server_key] = (
            server_totals.get(entry.server_key, 0) + entry.invocation_count
        )
    by_server = sorted(
        [
            McpServerSummary(
                server_key=sk,
                server_name=server_names.get(sk, sk),
                total_invocations=total,
            )
            for sk, total in server_totals.items()
        ],
        key=lambda s: s.total_invocations,
        reverse=True,
    )

    return McpToolUsageResponse(
        workspace_id=str(workspace_id),
        period_start=start_date,
        period_end=end_date,
        by_server=by_server,
        by_tool=by_tool,
    )


__all__ = ["router"]
