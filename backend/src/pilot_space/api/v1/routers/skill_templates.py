"""Skill template admin API endpoints (P20-05).

Admin CRUD for workspace skill templates.
- GET  /{workspace_id}/skill-templates         -> list templates (200)
- POST /{workspace_id}/skill-templates         -> create template (201, admin)
- PATCH /{workspace_id}/skill-templates/{id}   -> update template (200, admin)
- DELETE /{workspace_id}/skill-templates/{id}  -> soft-delete (204, admin)

Built-in templates are read-only: only is_active can be toggled.
All members can browse templates (GET). Mutations require ADMIN/OWNER.

Source: Phase 20, P20-05
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from pilot_space.api.middleware.request_context import WorkspaceId
from pilot_space.api.v1.schemas.skill_template import (
    SkillTemplateCreate,
    SkillTemplateSchema,
    SkillTemplateUpdate,
)
from pilot_space.dependencies import CurrentUserId, DbSession
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.database.repositories.skill_template_repository import (
    SkillTemplateRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/{workspace_id}/skill-templates",
    tags=["Skill Templates"],
)


async def _require_admin(user_id: UUID, workspace_id: UUID, session: DbSession) -> None:
    stmt = select(WorkspaceMember.role).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.is_active.is_(True),
        WorkspaceMember.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    row = result.scalar()
    if row is None:
        raise ForbiddenError("Not a member of this workspace")
    role = row.value if hasattr(row, "value") else str(row)
    if role not in (WorkspaceRole.ADMIN.value, WorkspaceRole.OWNER.value):
        raise ForbiddenError("Admin or owner role required")


@router.get(
    "",
    response_model=list[SkillTemplateSchema],
    status_code=status.HTTP_200_OK,
    summary="List skill templates for workspace",
    description="Returns all non-deleted templates. All workspace members can browse.",
)
async def list_skill_templates(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> list[SkillTemplateSchema]:
    """List all non-deleted skill templates in a workspace.

    Args:
        workspace_id: Workspace UUID from path.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        List of SkillTemplateSchema ordered by sort_order.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    repo = SkillTemplateRepository(session)
    templates = await repo.get_by_workspace(workspace_id)
    return [SkillTemplateSchema.model_validate(t) for t in templates]


@router.post(
    "",
    response_model=SkillTemplateSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace skill template",
    description="Admin-only. Creates a workspace-scoped template (source='workspace').",
)
async def create_skill_template(
    workspace_id: WorkspaceId,
    body: SkillTemplateCreate,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> SkillTemplateSchema:
    """Create a new workspace skill template.

    Args:
        workspace_id: Workspace UUID from path.
        body: Template creation payload.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        Created SkillTemplateSchema.

    Raises:
        ForbiddenError: 403 if not admin/owner.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    repo = SkillTemplateRepository(session)
    template = await repo.create(
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        skill_content=body.skill_content,
        icon=body.icon,
        sort_order=body.sort_order,
        source="workspace",
        role_type=body.role_type,
        created_by=current_user_id,
    )

    logger.info(
        "[SkillTemplates] Created template=%s workspace=%s user=%s",
        template.id,
        workspace_id,
        current_user_id,
    )

    return SkillTemplateSchema.model_validate(template)


@router.patch(
    "/{template_id}",
    response_model=SkillTemplateSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a skill template",
    description=(
        "Admin-only. Built-in templates only allow is_active toggle; "
        "other field changes return 403."
    ),
)
async def update_skill_template(
    workspace_id: WorkspaceId,
    template_id: UUID,
    body: SkillTemplateUpdate,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> SkillTemplateSchema:
    """Update a skill template.

    Built-in templates only allow is_active toggling. Attempts to change
    other fields on built-in templates return 403.

    Args:
        workspace_id: Workspace UUID from path.
        template_id: Template UUID from path.
        body: Update payload (partial).
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        Updated SkillTemplateSchema.

    Raises:
        ForbiddenError: 403 if not admin or trying to edit built-in fields.
        NotFoundError: 404 if template not found.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    repo = SkillTemplateRepository(session)
    template = await repo.get_by_id(template_id)

    if template is None or template.is_deleted:
        raise NotFoundError("Skill template not found")

    # Built-in templates: only is_active can be changed
    if template.source == "built_in":
        update_data = body.model_dump(exclude_unset=True)
        non_active_fields = {k for k in update_data if k != "is_active"}
        if non_active_fields:
            raise ForbiddenError("Built-in templates can only toggle is_active")

    # Apply updates
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    updated = await repo.update(template)

    logger.info(
        "[SkillTemplates] Updated template=%s workspace=%s user=%s",
        template_id,
        workspace_id,
        current_user_id,
    )

    return SkillTemplateSchema.model_validate(updated)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a skill template",
    description="Admin-only. Soft-deletes the template.",
)
async def delete_skill_template(
    workspace_id: WorkspaceId,
    template_id: UUID,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> None:
    """Soft-delete a skill template.

    Args:
        workspace_id: Workspace UUID from path.
        template_id: Template UUID from path.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Raises:
        ForbiddenError: 403 if not admin/owner.
        NotFoundError: 404 if template not found.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    repo = SkillTemplateRepository(session)
    result = await repo.soft_delete(template_id)

    if result is None:
        raise NotFoundError("Skill template not found")

    logger.info(
        "[SkillTemplates] Deleted template=%s workspace=%s user=%s",
        template_id,
        workspace_id,
        current_user_id,
    )


__all__ = ["router"]
