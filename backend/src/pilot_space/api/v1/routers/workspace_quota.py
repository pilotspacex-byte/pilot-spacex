"""Workspace quota management API router.

Provides endpoints for per-workspace rate limit and storage quota configuration.

Endpoints (all under /api/v1/workspaces/{workspace_slug}/settings/quota):
  GET    /                  — current quota stats (ADMIN or OWNER)
  PATCH  /                  — update quota columns (OWNER only)
  POST   /recalculate       — recount actual storage usage (OWNER only)

Storage enforcement helpers:
  _check_storage_quota()   — pre-write quota check; returns (allowed, pct)
  _update_storage_usage()  — post-write atomic delta update

TENANT-03 requirements:
  - X-Storage-Warning: {pct} header when workspace reaches 80% of quota
  - HTTP 507 Insufficient Storage when workspace reaches 100% of quota
  - PATCH invalidates Redis ws_limits:{workspace_id} cache immediately
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, field_validator
from sqlalchemy import text, update

from pilot_space.dependencies import RedisDep
from pilot_space.dependencies.auth import CurrentUser, SessionDep
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.permissions import check_permission
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(tags=["quota"])

WorkspaceSlugPath = Annotated[str, Path(description="Workspace slug or UUID")]


# ============================================================================
# Schemas
# ============================================================================


class QuotaResponse(BaseModel):
    """Response for GET /settings/quota."""

    rate_limit_standard_rpm: int | None
    rate_limit_ai_rpm: int | None
    storage_quota_mb: int | None
    storage_used_bytes: int
    storage_used_mb: float


class QuotaUpdateRequest(BaseModel):
    """Request body for PATCH /settings/quota.

    All fields are optional — send only the fields you want to change.
    Pass null to remove a custom limit (revert to system default).
    """

    rate_limit_standard_rpm: int | None = None
    rate_limit_ai_rpm: int | None = None
    storage_quota_mb: int | None = None

    @field_validator(
        "rate_limit_standard_rpm", "rate_limit_ai_rpm", "storage_quota_mb", mode="before"
    )
    @classmethod
    def must_be_positive_or_none(cls, v: Any) -> Any:
        """Validate that numeric fields are positive integers or None."""
        if v is not None and (not isinstance(v, int) or v <= 0):
            raise ValueError("Must be a positive integer or null")
        return v


class RecalculateResponse(BaseModel):
    """Response for POST /settings/quota/recalculate."""

    recalculated_bytes: int


# ============================================================================
# Internal helpers
# ============================================================================


async def _resolve_workspace(workspace_slug: str, session: AsyncSession) -> Workspace:
    """Resolve workspace slug or UUID to a Workspace model.

    Args:
        workspace_slug: URL path parameter (slug or UUID string).
        session: Database session.

    Returns:
        Workspace model instance.

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
    return workspace


async def _resolve_workspace_and_check_permission(
    workspace_slug: str,
    session: AsyncSession,
    user_id: UUID,
) -> Workspace:
    """Resolve workspace and assert settings:read permission (ADMIN or OWNER).

    Args:
        workspace_slug: URL path parameter (slug or UUID string).
        session: Database session.
        user_id: Requesting user UUID.

    Returns:
        Workspace model instance.

    Raises:
        HTTPException: 404 if workspace not found, 403 if insufficient permission.
    """
    workspace = await _resolve_workspace(workspace_slug, session)
    allowed = await check_permission(
        session,
        user_id,
        workspace.id,
        resource="settings",
        action="read",
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner access required to view quota settings",
        )
    return workspace


async def _resolve_workspace_and_check_manage(
    workspace_slug: str,
    session: AsyncSession,
    user_id: UUID,
) -> Workspace:
    """Resolve workspace and assert settings:manage permission (OWNER only).

    Args:
        workspace_slug: URL path parameter (slug or UUID string).
        session: Database session.
        user_id: Requesting user UUID.

    Returns:
        Workspace model instance.

    Raises:
        HTTPException: 404 if workspace not found, 403 if insufficient permission.
    """
    workspace = await _resolve_workspace(workspace_slug, session)
    allowed = await check_permission(
        session,
        user_id,
        workspace.id,
        resource="settings",
        action="manage",
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required to manage workspace quota settings",
        )
    return workspace


async def _check_storage_quota(
    session: AsyncSession,
    workspace_id: UUID,
    delta_bytes: int,
) -> tuple[bool, float | None]:
    """Pre-write storage quota check.

    Args:
        session: Database session.
        workspace_id: Workspace UUID.
        delta_bytes: Net byte change for the write (positive = growth, negative = shrink).

    Returns:
        Tuple of (allowed, warning_pct):
        - (True, None)  — allowed, no warning
        - (True, pct)   — allowed, but pct >= 0.80 → caller must add X-Storage-Warning header
        - (False, None) — blocked, caller must raise HTTP 507
    """
    workspace = await session.get(Workspace, workspace_id)
    if workspace is None:
        # Workspace not found — fail open (let the write proceed; endpoint will 404)
        return True, None

    if workspace.storage_quota_mb is None:
        # NULL quota = unlimited
        return True, None

    quota_bytes = workspace.storage_quota_mb * 1024 * 1024
    projected = workspace.storage_used_bytes + delta_bytes

    if projected > quota_bytes:
        return False, None

    if quota_bytes > 0:
        pct = projected / quota_bytes
        if pct >= 0.80:
            return True, pct

    return True, None


async def _update_storage_usage(
    session: AsyncSession,
    workspace_id: UUID,
    delta_bytes: int,
) -> None:
    """Atomically update storage_used_bytes by delta_bytes.

    Uses a SQL expression update to avoid race conditions when multiple
    writes happen concurrently.

    Args:
        session: Database session.
        workspace_id: Workspace UUID.
        delta_bytes: Change in bytes (positive or negative).
    """
    await session.execute(
        update(Workspace)
        .where(Workspace.id == workspace_id)
        .values(storage_used_bytes=Workspace.storage_used_bytes + delta_bytes)
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/{workspace_slug}/settings/quota")
async def get_workspace_quota(
    workspace_slug: WorkspaceSlugPath,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Return current rate limits and storage usage for a workspace.

    Requires settings:read permission (ADMIN or OWNER).

    Returns:
        QuotaResponse with rate_limit_standard_rpm, rate_limit_ai_rpm,
        storage_quota_mb, storage_used_bytes, storage_used_mb.
    """
    workspace = await _resolve_workspace_and_check_permission(
        workspace_slug, session, current_user.user_id
    )

    return {
        "rate_limit_standard_rpm": workspace.rate_limit_standard_rpm,
        "rate_limit_ai_rpm": workspace.rate_limit_ai_rpm,
        "storage_quota_mb": workspace.storage_quota_mb,
        "storage_used_bytes": workspace.storage_used_bytes,
        "storage_used_mb": round(workspace.storage_used_bytes / (1024 * 1024), 2),
    }


@router.patch("/{workspace_slug}/settings/quota")
async def patch_workspace_quota(
    workspace_slug: WorkspaceSlugPath,
    body: QuotaUpdateRequest,
    session: SessionDep,
    current_user: CurrentUser,
    redis: RedisDep,
) -> dict[str, Any]:
    """Update rate limit and storage quota columns for a workspace.

    Requires settings:manage permission (OWNER only).
    Invalidates Redis ws_limits:{workspace_id} cache on success.

    Args:
        workspace_slug: Workspace slug or UUID.
        body: Quota fields to update (all optional, pass null to revert to default).
        session: Database session.
        current_user: Authenticated user.
        redis: Redis client for cache invalidation (injected via RedisDep).

    Returns:
        Updated QuotaResponse.
    """
    workspace = await _resolve_workspace_and_check_manage(
        workspace_slug, session, current_user.user_id
    )

    # Apply partial update — only update fields explicitly provided in body
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workspace, field, value)

    await session.commit()
    await session.refresh(workspace)

    # Invalidate Redis rate limit cache so the new config is picked up immediately
    try:
        await redis.delete(f"ws_limits:{workspace.id}")
    except Exception:
        logger.exception(
            "Quota PATCH: failed to invalidate Redis cache for workspace %s",
            workspace.id,
        )

    return {
        "rate_limit_standard_rpm": workspace.rate_limit_standard_rpm,
        "rate_limit_ai_rpm": workspace.rate_limit_ai_rpm,
        "storage_quota_mb": workspace.storage_quota_mb,
        "storage_used_bytes": workspace.storage_used_bytes,
        "storage_used_mb": round(workspace.storage_used_bytes / (1024 * 1024), 2),
    }


@router.post("/{workspace_slug}/settings/quota/recalculate")
async def recalculate_storage_quota(
    workspace_slug: WorkspaceSlugPath,
    session: SessionDep,
    current_user: CurrentUser,
) -> RecalculateResponse:
    """Recount actual storage usage for a workspace (maintenance endpoint).

    Runs full storage recount:
      SELECT SUM(LENGTH(body)) FROM notes WHERE workspace_id=... +
      SELECT SUM(LENGTH(description)) FROM issues WHERE workspace_id=...

    Updates workspace.storage_used_bytes to the computed value.

    Requires settings:manage permission (OWNER only).

    Returns:
        RecalculateResponse with the recomputed storage_used_bytes.
    """
    workspace = await _resolve_workspace_and_check_manage(
        workspace_slug, session, current_user.user_id
    )

    # Compute total storage from notes + issues for this workspace
    notes_bytes_result = await session.execute(
        text(
            "SELECT COALESCE(SUM(LENGTH(body)), 0) FROM notes "
            "WHERE workspace_id = :workspace_id AND is_deleted = false"
        ).bindparams(workspace_id=str(workspace.id))
    )
    notes_bytes: int = notes_bytes_result.scalar() or 0

    issues_bytes_result = await session.execute(
        text(
            "SELECT COALESCE(SUM(LENGTH(description)), 0) FROM issues "
            "WHERE workspace_id = :workspace_id AND is_deleted = false"
        ).bindparams(workspace_id=str(workspace.id))
    )
    issues_bytes: int = issues_bytes_result.scalar() or 0

    total_bytes = notes_bytes + issues_bytes

    # Update workspace storage_used_bytes to the recalculated value
    await session.execute(
        update(Workspace).where(Workspace.id == workspace.id).values(storage_used_bytes=total_bytes)
    )
    await session.commit()

    logger.info(
        "Storage recalculated for workspace %s: %d bytes",
        workspace.id,
        total_bytes,
    )

    return RecalculateResponse(recalculated_bytes=total_bytes)


__all__ = [
    "QuotaResponse",
    "QuotaUpdateRequest",
    "RecalculateResponse",
    "_check_storage_quota",
    "_update_storage_usage",
    "router",
]
