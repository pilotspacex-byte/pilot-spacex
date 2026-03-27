"""Note templates CRUD API (T-144, Feature 016 M8).

Endpoints:
  GET    /workspaces/{workspace_id}/templates             -- list, member access
  POST   /workspaces/{workspace_id}/templates             -- create, admin/owner only
  GET    /workspaces/{workspace_id}/templates/{id}        -- get one, member access
  PUT    /workspaces/{workspace_id}/templates/{id}        -- update, admin/owner or creator
  DELETE /workspaces/{workspace_id}/templates/{id}        -- delete, admin/owner or creator

Thin HTTP shell -- all business logic delegated to NoteTemplateService.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from pilot_space.api.v1.dependencies import NoteTemplateServiceDep
from pilot_space.api.v1.schemas.note_template import (
    NoteTemplateCreate,
    NoteTemplateListResponse,
    NoteTemplateResponse,
    NoteTemplateUpdate,
)
from pilot_space.application.services.note_template import (
    CreateTemplatePayload,
    DeleteTemplatePayload,
    UpdateTemplatePayload,
)
from pilot_space.dependencies.auth import (
    CurrentUserId,
    SessionDep,
    require_workspace_admin,
    require_workspace_member,
)

router = APIRouter(tags=["Note Templates"])

WorkspaceIdPath = Annotated[UUID, Path(description="Workspace UUID")]
TemplateIdPath = Annotated[UUID, Path(description="Template UUID")]


@router.get(
    "/workspaces/{workspace_id}/templates",
    response_model=NoteTemplateListResponse,
)
async def list_templates(
    workspace_id: WorkspaceIdPath,
    db: SessionDep,
    service: NoteTemplateServiceDep,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> NoteTemplateListResponse:
    """List system templates + workspace custom templates. Member access."""
    rows = await service.list_templates(workspace_id)
    templates = [NoteTemplateResponse.model_validate(r) for r in rows]
    return NoteTemplateListResponse(templates=templates, total=len(templates))


@router.post(
    "/workspaces/{workspace_id}/templates",
    response_model=NoteTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    workspace_id: WorkspaceIdPath,
    payload: NoteTemplateCreate,
    db: SessionDep,
    current_user_id: CurrentUserId,
    service: NoteTemplateServiceDep,
    _: Annotated[UUID, Depends(require_workspace_admin)],
) -> NoteTemplateResponse:
    """Create a custom workspace template. Admin/owner only (FR-065)."""
    row = await service.create_template(
        CreateTemplatePayload(
            workspace_id=workspace_id,
            name=payload.name,
            description=payload.description or "",
            content=payload.content,
            created_by=current_user_id,
        )
    )
    return NoteTemplateResponse.model_validate(row)


@router.get(
    "/workspaces/{workspace_id}/templates/{template_id}",
    response_model=NoteTemplateResponse,
)
async def get_template(
    workspace_id: WorkspaceIdPath,
    template_id: TemplateIdPath,
    db: SessionDep,
    service: NoteTemplateServiceDep,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> NoteTemplateResponse:
    """Get a template by ID. System templates accessible to all members."""
    row = await service.get_template(template_id, workspace_id)
    return NoteTemplateResponse.model_validate(row)


@router.patch(
    "/workspaces/{workspace_id}/templates/{template_id}",
    response_model=NoteTemplateResponse,
)
async def update_template(
    workspace_id: WorkspaceIdPath,
    template_id: TemplateIdPath,
    payload: NoteTemplateUpdate,
    db: SessionDep,
    current_user_id: CurrentUserId,
    service: NoteTemplateServiceDep,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> NoteTemplateResponse:
    """Update a custom template. Admin/owner or creator. System templates are read-only."""
    row = await service.update_template(
        UpdateTemplatePayload(
            workspace_id=workspace_id,
            template_id=template_id,
            current_user_id=current_user_id,
            name=payload.name,
            description=payload.description,
            content=payload.content,
        )
    )
    return NoteTemplateResponse.model_validate(row)


@router.delete(
    "/workspaces/{workspace_id}/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_template(
    workspace_id: WorkspaceIdPath,
    template_id: TemplateIdPath,
    db: SessionDep,
    current_user_id: CurrentUserId,
    service: NoteTemplateServiceDep,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> None:
    """Delete a custom template. Admin/owner or creator. System templates cannot be deleted."""
    await service.delete_template(
        DeleteTemplatePayload(
            workspace_id=workspace_id,
            template_id=template_id,
            current_user_id=current_user_id,
        )
    )
