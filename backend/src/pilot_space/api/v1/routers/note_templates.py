"""Note templates CRUD API (T-144, Feature 016 M8).

Endpoints:
  GET    /workspaces/{workspace_id}/templates             — list, member access
  POST   /workspaces/{workspace_id}/templates             — create, admin/owner only
  GET    /workspaces/{workspace_id}/templates/{id}        — get one, member access
  PUT    /workspaces/{workspace_id}/templates/{id}        — update, admin/owner or creator
  DELETE /workspaces/{workspace_id}/templates/{id}        — delete, admin/owner or creator

System templates (is_system=true) are read-only and available to all workspaces.
Custom templates are scoped to a workspace and require admin/owner role to create.
RLS enforced by PostgreSQL policies (migration 044).
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated, Any
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Path, status

from pilot_space.api.v1.schemas.note_template import (
    NoteTemplateCreate,
    NoteTemplateListResponse,
    NoteTemplateResponse,
    NoteTemplateUpdate,
)
from pilot_space.dependencies.auth import (
    CurrentUserId,
    SessionDep,
    require_workspace_admin,
    require_workspace_member,
)
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Note Templates"])

WorkspaceIdPath = Annotated[UUID, Path(description="Workspace UUID")]
TemplateIdPath = Annotated[UUID, Path(description="Template UUID")]

# Allowlist of columns permitted in UPDATE SET clause.
# Any key not in this set is rejected to prevent SQL injection via dynamic column names.
_ALLOWED_UPDATE_COLUMNS: frozenset[str] = frozenset({"name", "description", "content"})

# ── Repository helpers ─────────────────────────────────────────────────────────

_SELECT_COLS = (
    "id, workspace_id, name, description, content, is_system, created_by, created_at, updated_at"
)


async def _get_template(db: Any, template_id: UUID) -> dict[str, Any] | None:
    result = await db.execute(
        sa.text(f"SELECT {_SELECT_COLS} FROM note_templates WHERE id = :id"),
        {"id": str(template_id)},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _list_templates(db: Any, workspace_id: UUID) -> list[dict[str, Any]]:
    result = await db.execute(
        sa.text(
            f"SELECT {_SELECT_COLS} FROM note_templates "
            "WHERE is_system = true OR workspace_id = :ws_id "
            "ORDER BY is_system DESC, created_at ASC"
        ),
        {"ws_id": str(workspace_id)},
    )
    return [dict(r) for r in result.mappings()]


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get(
    "/workspaces/{workspace_id}/templates",
    response_model=NoteTemplateListResponse,
)
async def list_templates(
    workspace_id: WorkspaceIdPath,
    db: SessionDep,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> NoteTemplateListResponse:
    """List system templates + workspace custom templates. Member access."""
    rows = await _list_templates(db, workspace_id)
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
    _: Annotated[UUID, Depends(require_workspace_admin)],
) -> NoteTemplateResponse:
    """Create a custom workspace template. Admin/owner only (FR-065)."""
    new_id = uuid.uuid4()

    await db.execute(
        sa.text(
            "INSERT INTO note_templates "
            "(id, workspace_id, name, description, content, is_system, created_by) "
            "VALUES (:id, :ws_id, :name, :description, :content::jsonb, false, :created_by)"
        ),
        {
            "id": str(new_id),
            "ws_id": str(workspace_id),
            "name": payload.name,
            "description": payload.description,
            "content": json.dumps(payload.content),
            "created_by": str(current_user_id),
        },
    )
    await db.commit()

    row = await _get_template(db, new_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Template creation failed."
        )

    logger.info("note_template_created", template_id=str(new_id), workspace_id=str(workspace_id))
    return NoteTemplateResponse.model_validate(row)


@router.get(
    "/workspaces/{workspace_id}/templates/{template_id}",
    response_model=NoteTemplateResponse,
)
async def get_template(
    workspace_id: WorkspaceIdPath,
    template_id: TemplateIdPath,
    db: SessionDep,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> NoteTemplateResponse:
    """Get a template by ID. System templates accessible to all members."""
    row = await _get_template(db, template_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    if not row["is_system"] and row["workspace_id"] != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return NoteTemplateResponse.model_validate(row)


@router.put(
    "/workspaces/{workspace_id}/templates/{template_id}",
    response_model=NoteTemplateResponse,
)
async def update_template(
    workspace_id: WorkspaceIdPath,
    template_id: TemplateIdPath,
    payload: NoteTemplateUpdate,
    db: SessionDep,
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> NoteTemplateResponse:
    """Update a custom template. Admin/owner or creator. System templates are read-only."""
    row = await _get_template(db, template_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    if row["is_system"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System templates are read-only.",
        )
    if row["workspace_id"] != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # Verify admin/owner or creator
    is_creator = str(row["created_by"]) == str(current_user_id) if row["created_by"] else False
    if not is_creator:
        result = await db.execute(
            sa.select(WorkspaceMember.role).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == current_user_id,
            )
        )
        role = result.scalar()
        if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    updates: dict[str, Any] = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.description is not None:
        updates["description"] = payload.description
    if payload.content is not None:
        updates["content"] = json.dumps(payload.content)

    if updates:
        for key in updates:
            if key not in _ALLOWED_UPDATE_COLUMNS:
                raise ValueError(f"Invalid update column: {key}")
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = str(template_id)
        await db.execute(
            sa.text(f"UPDATE note_templates SET {set_clause}, updated_at = now() WHERE id = :id"),
            updates,
        )
        await db.commit()

    updated = await _get_template(db, template_id)
    return NoteTemplateResponse.model_validate(updated)


@router.delete(
    "/workspaces/{workspace_id}/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_template(
    workspace_id: WorkspaceIdPath,
    template_id: TemplateIdPath,
    db: SessionDep,
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> None:
    """Delete a custom template. Admin/owner or creator. System templates cannot be deleted."""
    row = await _get_template(db, template_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    if row["is_system"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System templates cannot be deleted.",
        )
    if row["workspace_id"] != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    is_creator = str(row["created_by"]) == str(current_user_id) if row["created_by"] else False
    if not is_creator:
        result = await db.execute(
            sa.select(WorkspaceMember.role).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == current_user_id,
            )
        )
        role = result.scalar()
        if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    await db.execute(
        sa.text("DELETE FROM note_templates WHERE id = :id"),
        {"id": str(template_id)},
    )
    await db.commit()
    logger.info(
        "note_template_deleted", template_id=str(template_id), workspace_id=str(workspace_id)
    )
