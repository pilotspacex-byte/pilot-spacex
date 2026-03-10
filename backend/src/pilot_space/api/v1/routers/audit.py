"""Audit log API router — AUDIT-03, AUDIT-04, AUDIT-05, AUDIT-06.

Provides read-only and export endpoints for workspace audit logs.
NO write endpoints exist on individual audit entries — audit records
are immutable (enforced at DB layer by trigger).

Endpoints (all mounted under /workspaces/{workspace_slug}/audit):
  GET    /                 — filtered list with cursor pagination
  GET    /export           — streaming CSV or JSON export
  PATCH  /settings/retention — update workspace.audit_retention_days (OWNER only)

Authorization:
  - List and export require ADMIN or OWNER role (settings:read permission)
  - Retention update requires OWNER role (settings:manage permission)
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import AsyncIterator, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse

from pilot_space.api.v1.schemas.audit import (
    AuditLogPageResponse,
    AuditLogResponse,
    AuditRetentionRequest,
)
from pilot_space.api.v1.schemas.base import SuccessResponse
from pilot_space.dependencies.auth import CurrentUser, SessionDep
from pilot_space.infrastructure.database.models.audit_log import ActorType
from pilot_space.infrastructure.database.permissions import check_permission
from pilot_space.infrastructure.database.repositories.audit_log_repository import (
    AuditLogRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["audit"])

WorkspaceSlugPath = Annotated[str, Path(description="Workspace slug or UUID")]

# CSV columns in export order
_CSV_COLUMNS = [
    "timestamp",
    "actor_id",
    "actor_type",
    "action",
    "resource_type",
    "resource_id",
    "ip_address",
    "payload_json",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _resolve_workspace(
    workspace_slug: str,
    session: AsyncSession,
) -> UUID:
    """Resolve workspace slug (or UUID) to workspace.id.

    Args:
        workspace_slug: URL path parameter (slug or UUID string).
        session: Database session.

    Returns:
        Workspace UUID.

    Raises:
        HTTPException: 404 if workspace not found.
    """
    workspace_repo = WorkspaceRepository(session)
    try:
        as_uuid = UUID(workspace_slug)
        workspace = await workspace_repo.get_by_id_scalar(as_uuid)
    except ValueError:
        workspace = await workspace_repo.get_by_slug_scalar(workspace_slug)

    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace.id


async def _require_admin_or_owner(
    session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
) -> None:
    """Assert the user has settings:read permission (ADMIN or OWNER).

    Args:
        session: Database session.
        user_id: Requesting user UUID.
        workspace_id: Workspace being accessed.

    Raises:
        HTTPException: 403 if permission is not granted.
    """
    allowed = await check_permission(
        session,
        user_id,
        workspace_id,
        resource="settings",
        action="read",
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner access required to view audit logs",
        )


async def _require_owner(
    session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
) -> None:
    """Assert the user has settings:manage permission (OWNER only).

    Args:
        session: Database session.
        user_id: Requesting user UUID.
        workspace_id: Workspace being accessed.

    Raises:
        HTTPException: 403 if permission is not granted.
    """
    allowed = await check_permission(
        session,
        user_id,
        workspace_id,
        resource="settings",
        action="manage",
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required to configure audit retention",
        )


def _audit_log_to_response(row: object) -> AuditLogResponse:
    """Convert an AuditLog ORM row to AuditLogResponse schema.

    Args:
        row: AuditLog SQLAlchemy model instance.

    Returns:
        AuditLogResponse Pydantic schema.
    """
    return AuditLogResponse.model_validate(row)


def _audit_log_to_csv_dict(row: object) -> dict[str, str]:
    """Convert an AuditLog ORM row to a flat CSV dict.

    Args:
        row: AuditLog SQLAlchemy model instance.

    Returns:
        Dict with CSV column names as keys and string values.
    """
    from pilot_space.infrastructure.database.models.audit_log import AuditLog

    assert isinstance(row, AuditLog)
    return {
        "timestamp": row.created_at.isoformat() if row.created_at else "",
        "actor_id": str(row.actor_id) if row.actor_id else "",
        "actor_type": row.actor_type.value if row.actor_type else "",
        "action": row.action or "",
        "resource_type": row.resource_type or "",
        "resource_id": str(row.resource_id) if row.resource_id else "",
        "ip_address": row.ip_address or "",
        "payload_json": json.dumps(row.payload) if row.payload else "",
    }


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_slug}/audit
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_slug}/audit",
    response_model=AuditLogPageResponse,
    summary="List audit log entries with filtering and cursor pagination",
)
async def list_audit_log(
    workspace_slug: WorkspaceSlugPath,
    session: SessionDep,
    current_user: CurrentUser,
    actor_id: UUID | None = Query(default=None, description="Filter by actor UUID"),
    actor_type: ActorType | None = Query(
        default=None, description="Filter by actor type: AI, USER, or SYSTEM"
    ),
    action: str | None = Query(
        default=None, description="Filter by exact action string e.g. issue.create"
    ),
    resource_type: str | None = Query(
        default=None, description="Filter by resource type e.g. issue"
    ),
    start_date: datetime | None = Query(
        default=None, description="Inclusive lower bound for created_at (ISO 8601)"
    ),
    end_date: datetime | None = Query(
        default=None, description="Inclusive upper bound for created_at (ISO 8601)"
    ),
    cursor: str | None = Query(
        default=None, description="Opaque cursor for the next page (base64-encoded)"
    ),
    page_size: int = Query(default=50, ge=1, le=500, description="Items per page (max 500)"),
) -> AuditLogPageResponse:
    """Return a cursor-paginated, filtered list of audit log entries.

    Ordering: created_at DESC, id DESC (stable keyset sort).
    Requires ADMIN or OWNER role.

    Args:
        workspace_slug: Workspace slug or UUID.
        session: Database session.
        current_user: Authenticated user.
        actor_id: Optional actor UUID filter.
        actor_type: Optional actor type filter (AI, USER, or SYSTEM).
        action: Optional exact action filter.
        resource_type: Optional resource type filter.
        start_date: Optional inclusive start date filter.
        end_date: Optional inclusive end date filter.
        cursor: Optional pagination cursor from prior response.
        page_size: Number of items per page (1-500, default 50).

    Returns:
        AuditLogPageResponse with items, has_next, next_cursor.
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    await set_rls_context(session, current_user.user_id, workspace_id)
    await _require_admin_or_owner(session, current_user.user_id, workspace_id)

    repo = AuditLogRepository(session)
    page = await repo.list_filtered(
        workspace_id=workspace_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
        cursor=cursor,
        page_size=page_size,
    )

    return AuditLogPageResponse(
        items=[_audit_log_to_response(row) for row in page.items],
        has_next=page.has_next,
        next_cursor=page.next_cursor,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_slug}/audit/export
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_slug}/audit/export",
    summary="Stream audit log as CSV or JSON export",
)
async def export_audit_log(
    workspace_slug: WorkspaceSlugPath,
    session: SessionDep,
    current_user: CurrentUser,
    format: Literal["csv", "json"] = Query(
        default="json", description="Export format: csv or json"
    ),
    actor_id: UUID | None = Query(default=None, description="Filter by actor UUID"),
    actor_type: ActorType | None = Query(
        default=None, description="Filter by actor type: AI, USER, or SYSTEM"
    ),
    action: str | None = Query(default=None, description="Filter by exact action string"),
    resource_type: str | None = Query(default=None, description="Filter by resource type"),
    start_date: datetime | None = Query(
        default=None, description="Inclusive lower bound for created_at (ISO 8601)"
    ),
    end_date: datetime | None = Query(
        default=None, description="Inclusive upper bound for created_at (ISO 8601)"
    ),
) -> StreamingResponse:
    """Stream audit log entries as CSV or JSON.

    Uses yield_per(100) server-side cursor to avoid OOM on large exports.
    No row limit — frontend is responsible for warning on large exports.

    Requires ADMIN or OWNER role.

    Args:
        workspace_slug: Workspace slug or UUID.
        session: Database session.
        current_user: Authenticated user.
        format: "csv" or "json" (default "json").
        actor_id: Optional actor UUID filter.
        actor_type: Optional actor type filter (AI, USER, or SYSTEM).
        action: Optional exact action filter.
        resource_type: Optional resource type filter.
        start_date: Optional inclusive start date filter.
        end_date: Optional inclusive end date filter.

    Returns:
        StreamingResponse with appropriate Content-Type and Content-Disposition.
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    await set_rls_context(session, current_user.user_id, workspace_id)
    await _require_admin_or_owner(session, current_user.user_id, workspace_id)

    repo = AuditLogRepository(session)
    rows = await repo.list_for_export(
        workspace_id=workspace_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )

    if format == "csv":
        return StreamingResponse(
            _stream_csv(rows),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="audit-log.csv"',
            },
        )
    return StreamingResponse(
        _stream_json(rows),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="audit-log.json"',
        },
    )


async def _stream_csv(rows: Sequence[object]) -> AsyncIterator[bytes]:
    """Generator that yields CSV bytes row-by-row.

    Yields the header row first, then each data row individually to
    minimise peak memory use on large exports.

    Args:
        rows: List of AuditLog ORM instances.

    Yields:
        CSV bytes.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_COLUMNS)
    writer.writeheader()
    yield buf.getvalue().encode()
    buf.seek(0)
    buf.truncate()

    for row in rows:
        writer.writerow(_audit_log_to_csv_dict(row))
        yield buf.getvalue().encode()
        buf.seek(0)
        buf.truncate()


async def _stream_json(rows: Sequence[object]) -> AsyncIterator[bytes]:
    """Generator that yields JSON bytes as a streaming array.

    Opens the JSON array, yields each entry as a JSON object separated
    by commas, then closes the array.

    Args:
        rows: List of AuditLog ORM instances.

    Yields:
        JSON bytes.
    """
    yield b"["
    for i, row in enumerate(rows):
        entry = _audit_log_to_response(row).model_dump(mode="json")
        prefix = b"" if i == 0 else b","
        yield prefix + json.dumps(entry, default=str).encode()
    yield b"]"


# ---------------------------------------------------------------------------
# PATCH /workspaces/{workspace_slug}/audit/settings/retention
# ---------------------------------------------------------------------------


@router.patch(
    "/workspaces/{workspace_slug}/settings/audit-retention",
    response_model=SuccessResponse,
    summary="Update workspace audit log retention period",
)
async def update_audit_retention(
    workspace_slug: WorkspaceSlugPath,
    body: AuditRetentionRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> SuccessResponse:
    """Update the audit_retention_days setting for a workspace.

    Requires OWNER role (settings:manage permission).

    Args:
        workspace_slug: Workspace slug or UUID.
        body: AuditRetentionRequest with audit_retention_days (1-3650).
        session: Database session.
        current_user: Authenticated user.

    Returns:
        SuccessResponse confirming the update.
    """
    from sqlalchemy import update

    from pilot_space.infrastructure.database.models.workspace import Workspace

    workspace_id = await _resolve_workspace(workspace_slug, session)
    await set_rls_context(session, current_user.user_id, workspace_id)
    await _require_owner(session, current_user.user_id, workspace_id)

    stmt = (
        update(Workspace)
        .where(Workspace.id == workspace_id)
        .values(audit_retention_days=body.audit_retention_days)
    )
    await session.execute(stmt)
    await session.commit()

    return SuccessResponse(
        success=True,
        message=f"Audit retention updated to {body.audit_retention_days} days",
    )


__all__ = ["router"]
