"""Workspace hooks CRUD API -- admin-managed declarative hook rules.

Phase 83 -- thin HTTP shell for ``HookRuleService``. Follows the
``ai_permissions.py`` router pattern: member-readable list, admin-only
mutations. All service exceptions propagate to the global error handler.

Endpoints (mounted under ``/api/v1/workspaces/{workspace_id}/hooks``):

* ``GET    ""``           -- list hook rules (member)
* ``POST   ""``           -- create hook rule (admin)
* ``PUT    "/{hook_id}"`` -- update hook rule (admin)
* ``DELETE "/{hook_id}"`` -- delete hook rule (admin)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response, status

from pilot_space.api.v1.dependencies import HookRuleServiceDep
from pilot_space.api.v1.schemas.hook_rule import (
    CreateHookRuleRequest,
    HookRuleListResponse,
    HookRuleResponse,
    UpdateHookRuleRequest,
)
from pilot_space.dependencies.auth import (
    CurrentUser,
    DbSession,
    WorkspaceAdminId,
    WorkspaceMemberId,
)
from pilot_space.infrastructure.database.models.workspace_hook_config import (
    WorkspaceHookConfig,
)

router = APIRouter(tags=["workspace-hooks"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_response(hook: WorkspaceHookConfig) -> HookRuleResponse:
    """Convert WorkspaceHookConfig ORM model to response schema."""
    return HookRuleResponse(
        id=str(hook.id),
        name=hook.name,
        tool_pattern=hook.tool_pattern,
        action=hook.action,
        event_type=hook.event_type,
        priority=hook.priority,
        is_enabled=hook.is_enabled,
        description=hook.description,
        created_by=str(hook.created_by),
        updated_by=str(hook.updated_by),
        created_at=hook.created_at,
        updated_at=hook.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_hook_rules(
    workspace_id: WorkspaceMemberId,
    session: DbSession,
    service: HookRuleServiceDep,
) -> HookRuleListResponse:
    """List all hook rules for a workspace (including disabled).

    Members can read hook rules to understand workspace tool policies.
    """
    _ = session  # ContextVar population -- required for DI session lookup.
    rules = await service.list_rules(workspace_id, include_disabled=True)
    responses = [_to_response(r) for r in rules]
    return HookRuleListResponse(rules=responses, count=len(responses))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_hook_rule(
    workspace_id: WorkspaceAdminId,
    body: CreateHookRuleRequest,
    current_user: CurrentUser,
    session: DbSession,
    service: HookRuleServiceDep,
) -> HookRuleResponse:
    """Create a new hook rule for a workspace.

    Admin-only. Service validates pattern and enforces 50-rule limit.
    """
    _ = session
    hook = await service.create(
        workspace_id=workspace_id,
        name=body.name,
        tool_pattern=body.tool_pattern,
        action=body.action,
        event_type=body.event_type,
        priority=body.priority,
        description=body.description,
        actor_user_id=current_user.user_id,
    )
    return _to_response(hook)


@router.put("/{hook_id}")
async def update_hook_rule(
    workspace_id: WorkspaceAdminId,
    hook_id: UUID,
    body: UpdateHookRuleRequest,
    current_user: CurrentUser,
    session: DbSession,
    service: HookRuleServiceDep,
) -> HookRuleResponse:
    """Update an existing hook rule.

    Admin-only. Service validates workspace ownership and re-validates
    the pattern if changed.
    """
    _ = session
    update_data = body.model_dump(exclude_unset=True)
    hook = await service.update(
        workspace_id=workspace_id,
        hook_id=hook_id,
        actor_user_id=current_user.user_id,
        **update_data,
    )
    return _to_response(hook)


@router.delete("/{hook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hook_rule(
    workspace_id: WorkspaceAdminId,
    hook_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    service: HookRuleServiceDep,
) -> Response:
    """Delete a hook rule.

    Admin-only. Service validates workspace ownership before deletion.
    """
    _ = session
    await service.delete(
        workspace_id=workspace_id,
        hook_id=hook_id,
        actor_user_id=current_user.user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
