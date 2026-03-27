"""Super-admin operator dashboard routes -- TENANT-04.

These routes bypass workspace JWT auth entirely. Access is controlled by
PILOT_SPACE_SUPER_ADMIN_TOKEN bearer token (see dependencies/admin.py).

Uses service_role DB connection -- RLS is bypassed for cross-workspace queries.
All responses are read-only; no workspace data is mutated via admin routes.

Endpoints:
    GET /workspaces             -- list all workspaces with health metrics
    GET /workspaces/{slug}      -- workspace detail with member activity and AI actions
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from pilot_space.api.v1.dependencies import AdminDashboardServiceDep
from pilot_space.dependencies.admin import get_super_admin
from pilot_space.schemas.admin_dashboard import WorkspaceDetail, WorkspaceOverview

logger = logging.getLogger(__name__)

router = APIRouter(tags=["super-admin"])


@router.get("/workspaces")
async def list_workspaces(
    _: Annotated[None, Depends(get_super_admin)],
    service: AdminDashboardServiceDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[WorkspaceOverview]:
    """List all workspaces with aggregated health metrics.

    Returns workspace list with member counts, owner email, storage usage,
    AI action counts, and rate-limit violation counts (from Redis).

    Requires: PILOT_SPACE_SUPER_ADMIN_TOKEN bearer token.
    """
    logger.info("super_admin_access", extra={"action": "list_workspaces", "token": "****"})
    return await service.list_workspaces(limit=limit, offset=offset)


@router.get("/workspaces/{workspace_slug}")
async def get_workspace_detail(
    workspace_slug: str,
    _: Annotated[None, Depends(get_super_admin)],
    service: AdminDashboardServiceDep,
) -> WorkspaceDetail:
    """Get workspace detail with member activity and AI action history.

    Returns:
        Workspace summary + top 5 active members + last 10 AI actions
        + quota config + rate-limit violation count.

    Requires: PILOT_SPACE_SUPER_ADMIN_TOKEN bearer token.
    """
    logger.info("super_admin_access", extra={"action": "workspace_detail"})
    return await service.get_workspace_detail(workspace_slug)
