"""AI tool permissions API — per-workspace granular tool policy CRUD.

Phase 69 — DD-003 granular tool permissions. Thin HTTP shell delegating
to ``PermissionService``. Member-readable list + audit log; admin-only
mutations. All service exceptions (InvalidPolicyError → 422, etc.)
propagate to the global ``app_error_handler``.

Endpoints (mounted under ``/api/v1/workspaces/{workspace_id}/ai/permissions``):

* ``GET    ""``                    — list resolved tool permissions (member)
* ``PUT    "/{tool_name}"``        — set mode for a single tool (admin)
* ``POST   "/template/{name}"``    — bulk-apply named template (admin)
* ``GET    "/audit-log"``          — paginated mode-change audit log (admin)
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, Field

from pilot_space.api.v1.dependencies import PermissionServiceDep
from pilot_space.dependencies.auth import (
    CurrentUser,
    DbSession,
    WorkspaceAdminId,
    WorkspaceMemberId,
)
from pilot_space.domain.permissions.tool_permission_mode import ToolPermissionMode

router = APIRouter(tags=["ai-permissions"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ToolPermissionResponse(BaseModel):
    """Resolved permission row for a single tool."""

    tool_name: str
    mode: ToolPermissionMode
    source: Literal["db", "override", "default"]
    can_set_auto: bool


class SetToolPermissionRequest(BaseModel):
    """Request body for ``PUT /{tool_name}``."""

    mode: ToolPermissionMode = Field(..., description="auto | ask | deny")


class ApplyTemplateResponse(BaseModel):
    """Result of a bulk template apply."""

    template: str
    applied: int
    skipped: list[str]


class AuditLogEntry(BaseModel):
    """Single audit-log row."""

    id: UUID
    tool_name: str
    old_mode: str | None
    new_mode: str
    actor_user_id: UUID
    reason: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_tool_permissions(
    workspace_id: WorkspaceMemberId,
    session: DbSession,
    service: PermissionServiceDep,
) -> list[ToolPermissionResponse]:
    """Return every known tool merged with DB overrides + DD-003 defaults."""
    _ = session  # ContextVar population — required for DI session lookup.
    rows = await service.list_all(workspace_id)
    return [
        ToolPermissionResponse(
            tool_name=row.tool_name,
            mode=row.mode,
            source=row.source,  # type: ignore[arg-type]
            can_set_auto=row.can_set_auto,
        )
        for row in rows
    ]


@router.put("/{tool_name}")
async def set_tool_permission(
    workspace_id: WorkspaceAdminId,
    tool_name: Annotated[str, Path(description="Fully-qualified MCP tool name")],
    body: SetToolPermissionRequest,
    current_user: CurrentUser,
    session: DbSession,
    service: PermissionServiceDep,
) -> ToolPermissionResponse:
    """Set the mode for a single tool. DD-003 enforced by the service."""
    _ = session
    await service.set(
        workspace_id=workspace_id,
        tool_name=tool_name,
        mode=body.mode,
        actor_user_id=current_user.user_id,
    )
    # Re-resolve and return the row so the client sees source=db.
    resolved = await service.list_all(workspace_id)
    match = next((r for r in resolved if r.tool_name == tool_name), None)
    if match is None:
        # Tool name not in ALL_TOOL_NAMES — still return the raw mode.
        return ToolPermissionResponse(
            tool_name=tool_name,
            mode=body.mode,
            source="db",
            can_set_auto=True,
        )
    return ToolPermissionResponse(
        tool_name=match.tool_name,
        mode=match.mode,
        source=match.source,  # type: ignore[arg-type]
        can_set_auto=match.can_set_auto,
    )


@router.post("/template/{template_name}")
async def apply_template(
    workspace_id: WorkspaceAdminId,
    template_name: Annotated[str, Path(description="conservative | standard | trusted")],
    current_user: CurrentUser,
    session: DbSession,
    service: PermissionServiceDep,
) -> ApplyTemplateResponse:
    """Bulk-apply a named policy template to every tool."""
    _ = session
    result = await service.bulk_apply_template(
        workspace_id=workspace_id,
        template_name=template_name,
        actor_user_id=current_user.user_id,
    )
    return ApplyTemplateResponse(
        template=result.template,
        applied=result.applied,
        skipped=list(result.skipped),
    )


@router.get("/audit-log")
async def list_audit_log(
    workspace_id: WorkspaceAdminId,
    session: DbSession,
    service: PermissionServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AuditLogEntry]:
    """Return mode-change audit log rows, most-recent first."""
    _ = session
    rows = await service.list_audit_log(workspace_id, limit=limit, offset=offset)
    return [
        AuditLogEntry(
            id=row.id,
            tool_name=row.tool_name,
            old_mode=row.old_mode,
            new_mode=row.new_mode,
            actor_user_id=row.actor_user_id,
            reason=row.reason,
            created_at=row.created_at,
        )
        for row in rows
    ]


__all__ = ["router"]
