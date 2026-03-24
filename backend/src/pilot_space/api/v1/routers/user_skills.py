"""User skill API endpoints (P20-06).

Member CRUD for personalized user skills.
- GET  /{workspace_id}/user-skills          -> list user's skills (200)
- POST /{workspace_id}/user-skills          -> create from template (201)
- PATCH /{workspace_id}/user-skills/{id}    -> toggle is_active / update (200)
- DELETE /{workspace_id}/user-skills/{id}   -> soft-delete (204)

All operations scoped to the authenticated user's own skills.
POST delegates to CreateUserSkillService for AI personalization.

Source: Phase 20, P20-06
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from pilot_space.api.middleware import create_problem_response
from pilot_space.api.middleware.request_context import WorkspaceId
from pilot_space.api.v1.schemas.user_skill import (
    UserSkillCreate,
    UserSkillSchema,
    UserSkillUpdate,
)
from pilot_space.application.services.user_skill.create_user_skill_service import (
    CreateUserSkillService,
)
from pilot_space.dependencies import CurrentUserId, DbSession
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.infrastructure.database.repositories.user_skill_repository import (
    UserSkillRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/{workspace_id}/user-skills",
    tags=["User Skills"],
)


def _to_schema(skill: object) -> UserSkillSchema:
    """Convert a UserSkill model to schema, adding computed template_name.

    Args:
        skill: UserSkill SQLAlchemy model instance.

    Returns:
        UserSkillSchema with template_name populated from joined template.
    """
    data = UserSkillSchema.model_validate(skill)
    # Only access template relationship if template_id is set (avoids lazy='raise')
    if getattr(skill, "template_id", None) is not None:
        template = getattr(skill, "template", None)
        if template is not None:
            data.template_name = getattr(template, "name", None)
    return data


@router.get(
    "",
    response_model=list[UserSkillSchema],
    status_code=status.HTTP_200_OK,
    summary="List user's skills in workspace",
    description="Returns the authenticated user's active skills in the workspace.",
)
async def list_user_skills(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> list[UserSkillSchema]:
    """List the current user's active skills in a workspace.

    Args:
        workspace_id: Workspace UUID from path.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        List of UserSkillSchema for the current user.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    repo = UserSkillRepository(session)
    skills = await repo.get_by_user_workspace(current_user_id, workspace_id)
    return [_to_schema(s) for s in skills]


@router.post(
    "",
    response_model=UserSkillSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create user skill from template",
    description=(
        "Creates a personalized skill from a template. "
        "AI generates content based on the user's experience description."
    ),
)
async def create_user_skill(
    workspace_id: WorkspaceId,
    body: UserSkillCreate,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> UserSkillSchema | JSONResponse:
    """Create a user skill from a template.

    Delegates to CreateUserSkillService for template validation,
    duplicate checking, and AI personalization.

    Args:
        workspace_id: Workspace UUID from path.
        body: Template ID and optional experience description.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        Created UserSkillSchema or RFC 7807 problem response on error.
    """
    await set_rls_context(session, current_user_id, workspace_id)

    if not body.template_id and not body.skill_content:
        return create_problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either template_id or skill_content is required",
        )

    svc = CreateUserSkillService(session)
    skill = await svc.create(
        user_id=current_user_id,
        workspace_id=workspace_id,
        template_id=body.template_id,
        experience_description=body.experience_description or "",
        skill_content=body.skill_content,
        skill_name=body.skill_name,
        tags=body.tags if body.tags else None,
        usage=body.usage,
    )

    logger.info(
        "[UserSkills] Created skill=%s user=%s workspace=%s",
        skill.id,
        current_user_id,
        workspace_id,
    )

    return _to_schema(skill)


@router.patch(
    "/{skill_id}",
    response_model=UserSkillSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a user skill",
    description="Toggle is_active or update experience_description. Owner only.",
)
async def update_user_skill(
    workspace_id: WorkspaceId,
    skill_id: UUID,
    body: UserSkillUpdate,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> UserSkillSchema:
    """Update a user skill (is_active toggle or experience update).

    Only the skill owner can update their own skills.

    Args:
        workspace_id: Workspace UUID from path.
        skill_id: Skill UUID from path.
        body: Update payload (partial).
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        Updated UserSkillSchema.

    Raises:
        HTTPException: 404 if not found, 403 if not owner.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    repo = UserSkillRepository(session)
    # is_deleted is filtered inside get_by_id_with_template query
    skill = await repo.get_by_id_with_template(skill_id)

    if skill is None or skill.workspace_id != workspace_id:
        raise NotFoundError("User skill not found")

    if skill.user_id != current_user_id:
        raise ForbiddenError("Can only update your own skills")

    update_data = body.model_dump(exclude_unset=True)
    # Coerce tags=None to empty list to avoid NOT NULL constraint violation
    if "tags" in update_data and update_data["tags"] is None:
        update_data["tags"] = []
    for field, value in update_data.items():
        setattr(skill, field, value)

    updated = await repo.update(skill)

    logger.info(
        "[UserSkills] Updated skill=%s user=%s workspace=%s",
        skill_id,
        current_user_id,
        workspace_id,
    )

    return _to_schema(updated)


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user skill",
    description="Soft-delete a user skill. Owner only.",
)
async def delete_user_skill(
    workspace_id: WorkspaceId,
    skill_id: UUID,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> None:
    """Soft-delete a user skill.

    Only the skill owner can delete their own skills.

    Args:
        workspace_id: Workspace UUID from path.
        skill_id: Skill UUID from path.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Raises:
        HTTPException: 404 if not found, 403 if not owner.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    repo = UserSkillRepository(session)
    # is_deleted is filtered inside get_by_id_with_template query
    skill = await repo.get_by_id_with_template(skill_id)

    if skill is None or skill.workspace_id != workspace_id:
        raise NotFoundError("User skill not found")

    if skill.user_id != current_user_id:
        raise ForbiddenError("Can only delete your own skills")

    await repo.soft_delete(skill_id)

    logger.info(
        "[UserSkills] Deleted skill=%s user=%s workspace=%s",
        skill_id,
        current_user_id,
        workspace_id,
    )


__all__ = ["router"]
