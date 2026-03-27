"""Workspace action buttons REST API endpoints (SKBTN-01..04).

Thin HTTP shell — all business logic delegated to ActionButtonService.
Admin-only endpoints for action button CRUD, reorder, and toggle.
Members can list active buttons.

Source: Phase 17, SKBTN-01..04
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from pilot_space.api.v1.dependencies import ActionButtonServiceDep
from pilot_space.api.v1.schemas.skill_action_button import (
    SkillActionButtonCreate,
    SkillActionButtonReorder,
    SkillActionButtonResponse,
    SkillActionButtonUpdate,
)
from pilot_space.dependencies.auth import SessionDep, WorkspaceAdminId, WorkspaceMemberId

router = APIRouter(
    prefix="/{workspace_id}/action-buttons",
    tags=["Action Buttons"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[SkillActionButtonResponse],
    summary="List active action buttons",
)
async def list_active_buttons(
    workspace_id: WorkspaceMemberId,
    session: SessionDep,
    service: ActionButtonServiceDep,
) -> list[SkillActionButtonResponse]:
    """Return active action buttons for all workspace members."""
    buttons = await service.list_active(workspace_id)
    return [SkillActionButtonResponse.model_validate(b) for b in buttons]


@router.get(
    "/admin",
    response_model=list[SkillActionButtonResponse],
    summary="List all action buttons (admin)",
)
async def list_all_buttons(
    workspace_id: WorkspaceAdminId,
    session: SessionDep,
    service: ActionButtonServiceDep,
) -> list[SkillActionButtonResponse]:
    """Return all action buttons including inactive (admin only)."""
    buttons = await service.list_all(workspace_id)
    return [SkillActionButtonResponse.model_validate(b) for b in buttons]


@router.post(
    "",
    response_model=SkillActionButtonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an action button",
)
async def create_button(
    workspace_id: WorkspaceAdminId,
    request: SkillActionButtonCreate,
    session: SessionDep,
    service: ActionButtonServiceDep,
) -> SkillActionButtonResponse:
    """Create a new action button (admin only)."""
    created = await service.create(
        workspace_id,
        name=request.name,
        icon=request.icon,
        binding_type=request.binding_type,
        binding_id=request.binding_id,
        binding_metadata=request.binding_metadata,
    )
    return SkillActionButtonResponse.model_validate(created)


@router.patch(
    "/{button_id}",
    response_model=SkillActionButtonResponse,
    summary="Update an action button",
)
async def update_button(
    workspace_id: WorkspaceAdminId,
    button_id: UUID,
    request: SkillActionButtonUpdate,
    session: SessionDep,
    service: ActionButtonServiceDep,
) -> SkillActionButtonResponse:
    """Update an existing action button (admin only)."""
    update_data = request.model_dump(exclude_unset=True)
    updated = await service.update(workspace_id, button_id, update_data)
    return SkillActionButtonResponse.model_validate(updated)


@router.put(
    "/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reorder action buttons",
)
async def reorder_buttons(
    workspace_id: WorkspaceAdminId,
    request: SkillActionButtonReorder,
    session: SessionDep,
    service: ActionButtonServiceDep,
) -> None:
    """Reorder action buttons by providing ordered list of IDs (admin only)."""
    await service.reorder(workspace_id, request.button_ids)


@router.delete(
    "/{button_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an action button",
)
async def delete_button(
    workspace_id: WorkspaceAdminId,
    button_id: UUID,
    session: SessionDep,
    service: ActionButtonServiceDep,
) -> None:
    """Soft-delete an action button (admin only)."""
    await service.delete(workspace_id, button_id)


__all__ = ["router"]
