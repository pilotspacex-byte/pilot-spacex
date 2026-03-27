"""AI Governance API -- policy CRUD, BYOK status, artifact rollback.

Thin HTTP shell delegating to GovernanceRollbackService.

Endpoints:
  GET  /workspaces/{slug}/settings/ai-policy                        -- list policy matrix
  PUT  /workspaces/{slug}/settings/ai-policy/{role}/{action_type}  -- upsert policy row
  DEL  /workspaces/{slug}/settings/ai-policy/{role}/{action_type}  -- delete policy row
  GET  /workspaces/{slug}/settings/ai-status                        -- BYOK status
  POST /workspaces/{slug}/audit/{entry_id}/rollback                  -- rollback AI artifact

Authorization:
  - GET/PUT/DELETE policy: ADMIN or OWNER role (settings:read for GET, settings:manage for write)
  - GET ai-status: ADMIN or OWNER role
  - POST rollback: OWNER only

Requirements: AIGOV-01, AIGOV-02, AIGOV-04, AIGOV-05
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, status

from pilot_space.api.v1.dependencies import GovernanceRollbackServiceDep
from pilot_space.api.v1.schemas.ai_governance import (
    AIStatusResponse,
    PolicyRowIn,
    PolicyRowResponse,
)
from pilot_space.dependencies.auth import CurrentUser, SessionDep

router = APIRouter(tags=["ai-governance"])


# ---------------------------------------------------------------------------
# Policy CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_slug}/settings/ai-policy")
async def get_ai_policy(
    workspace_slug: Annotated[str, Path(description="Workspace slug or UUID")],
    current_user: CurrentUser,
    session: SessionDep,
    service: GovernanceRollbackServiceDep,
) -> list[PolicyRowResponse]:
    """Return all policy rows for the workspace."""
    rows = await service.list_policies(workspace_slug, current_user.user_id)
    return [
        PolicyRowResponse(
            role=r.role, action_type=r.action_type, requires_approval=r.requires_approval
        )
        for r in rows
    ]


@router.put("/workspaces/{workspace_slug}/settings/ai-policy/{role}/{action_type}")
async def set_ai_policy(
    workspace_slug: Annotated[str, Path(description="Workspace slug or UUID")],
    role: Annotated[str, Path(description="Role to configure (ADMIN, MEMBER, GUEST)")],
    action_type: Annotated[str, Path(description="Action type string")],
    body: PolicyRowIn,
    current_user: CurrentUser,
    session: SessionDep,
    service: GovernanceRollbackServiceDep,
) -> PolicyRowResponse:
    """Upsert a policy row for the given role and action_type."""
    result = await service.upsert_policy(
        workspace_slug, current_user.user_id, role, action_type, body.requires_approval
    )
    return PolicyRowResponse(
        role=result.role, action_type=result.action_type, requires_approval=result.requires_approval
    )


@router.delete(
    "/workspaces/{workspace_slug}/settings/ai-policy/{role}/{action_type}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_ai_policy(
    workspace_slug: Annotated[str, Path(description="Workspace slug or UUID")],
    role: Annotated[str, Path(description="Role")],
    action_type: Annotated[str, Path(description="Action type string")],
    current_user: CurrentUser,
    session: SessionDep,
    service: GovernanceRollbackServiceDep,
) -> None:
    """Delete a policy row, reverting to hardcoded defaults."""
    await service.delete_policy(workspace_slug, current_user.user_id, role, action_type)


# ---------------------------------------------------------------------------
# AI status endpoint
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_slug}/settings/ai-status")
async def get_ai_status(
    workspace_slug: Annotated[str, Path(description="Workspace slug or UUID")],
    current_user: CurrentUser,
    session: SessionDep,
    service: GovernanceRollbackServiceDep,
) -> AIStatusResponse:
    """Return BYOK configuration status for the workspace."""
    result = await service.get_ai_status(workspace_slug, current_user.user_id)
    return AIStatusResponse(
        byok_configured=result.byok_configured, providers=list(result.providers)
    )


# ---------------------------------------------------------------------------
# Rollback endpoint
# ---------------------------------------------------------------------------


@router.post("/workspaces/{workspace_slug}/audit/{entry_id}/rollback")
async def rollback_ai_artifact(
    workspace_slug: Annotated[str, Path(description="Workspace slug or UUID")],
    entry_id: Annotated[UUID, Path(description="Audit log entry UUID to rollback")],
    current_user: CurrentUser,
    session: SessionDep,
    service: GovernanceRollbackServiceDep,
) -> dict[str, str]:
    """Roll back an AI-created or AI-modified artifact to its pre-AI state."""
    result = await service.execute_rollback(workspace_slug, entry_id, current_user.user_id)
    return {"status": result.status, "entry_id": str(result.entry_id)}


__all__ = ["router"]
