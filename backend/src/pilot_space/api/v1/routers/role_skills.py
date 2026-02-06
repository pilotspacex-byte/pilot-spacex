"""Role skills API router.

Endpoints for role templates and user role skill management.

Source: 011-role-based-skills, T011
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from pilot_space.api.v1.schemas.role_skill import (
    CreateRoleSkillRequest,
    GenerateRoleSkillRequest,
    GenerateRoleSkillResponse,
    RegenerateRoleSkillRequest,
    RegenerateRoleSkillResponse,
    RoleSkillListResponse,
    RoleSkillResponse,
    RoleTemplateListResponse,
    RoleTemplateResponse,
    UpdateRoleSkillRequest,
)
from pilot_space.application.services.role_skill import (
    CreateRoleSkillPayload,
    CreateRoleSkillService,
    DeleteRoleSkillPayload,
    DeleteRoleSkillService,
    GenerateRoleSkillPayload,
    GenerateRoleSkillService,
    ListRoleSkillsPayload,
    ListRoleSkillsService,
    UpdateRoleSkillPayload,
    UpdateRoleSkillService,
)
from pilot_space.application.services.role_skill.generate_role_skill_service import (
    SkillGenerationRateLimitError,
)
from pilot_space.dependencies import CurrentUser, CurrentUserId, DbSession, WorkspaceMemberId

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Role Templates Router (no workspace scope)
# ---------------------------------------------------------------------------

role_templates_router = APIRouter(prefix="/role-templates", tags=["role-skills"])


@role_templates_router.get(
    "",
    response_model=RoleTemplateListResponse,
    summary="List all role templates",
    description="Returns predefined SDLC role templates for the role selection UI.",
)
async def list_role_templates(
    session: DbSession,
    _current_user: CurrentUser,
) -> RoleTemplateListResponse:
    """List all role templates.

    FR-001: Display predefined SDLC role templates.
    """
    from pilot_space.infrastructure.database.repositories.role_skill_repository import (
        RoleTemplateRepository,
    )

    repo = RoleTemplateRepository(session)
    templates = await repo.get_all_ordered()

    return RoleTemplateListResponse(
        templates=[
            RoleTemplateResponse(
                id=t.id,
                role_type=t.role_type,
                display_name=t.display_name,
                description=t.description,
                icon=t.icon,
                sort_order=t.sort_order,
                version=t.version,
                default_skill_content=t.default_skill_content,
            )
            for t in templates
        ]
    )


# ---------------------------------------------------------------------------
# Role Skills Router (workspace-scoped)
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/workspaces/{workspace_id}/role-skills", tags=["role-skills"])


@router.get(
    "",
    response_model=RoleSkillListResponse,
    summary="List user's role skills",
    description="Get the current user's role skills for a workspace.",
)
async def list_role_skills(
    workspace_id: UUID,
    session: DbSession,
    _member_id: WorkspaceMemberId,
    current_user_id: CurrentUserId,
) -> RoleSkillListResponse:
    """List role skills for current user in workspace.

    FR-009: View configured role skills.
    """
    service = ListRoleSkillsService(session)
    result = await service.execute(
        ListRoleSkillsPayload(user_id=current_user_id, workspace_id=workspace_id)
    )

    return RoleSkillListResponse(
        skills=[
            RoleSkillResponse(
                id=s.id,
                role_type=s.role_type,
                role_name=s.role_name,
                skill_content=s.skill_content,
                experience_description=s.experience_description,
                is_primary=s.is_primary,
                template_version=s.template_version,
                template_update_available=s.template_update_available,
                word_count=s.word_count,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in result.skills
        ]
    )


@router.post(
    "",
    response_model=RoleSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a role skill",
    description="Create a new role skill for the current user in a workspace.",
)
async def create_role_skill(
    workspace_id: UUID,
    request: CreateRoleSkillRequest,
    session: DbSession,
    _member_id: WorkspaceMemberId,
    current_user_id: CurrentUserId,
) -> RoleSkillResponse:
    """Create a new role skill.

    FR-002: Create role skill during onboarding or settings.
    FR-018: Max 3 roles per user-workspace.
    FR-020: Guests cannot create skills.
    """
    service = CreateRoleSkillService(session)

    try:
        skill = await service.execute(
            CreateRoleSkillPayload(
                user_id=current_user_id,
                workspace_id=workspace_id,
                role_type=request.role_type,
                role_name=request.role_name,
                skill_content=request.skill_content,
                experience_description=request.experience_description,
                is_primary=request.is_primary,
            )
        )
    except ValueError as e:
        error_msg = str(e)
        if "Maximum" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            ) from e
        if "already exists" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        ) from e

    return RoleSkillResponse(
        id=skill.id,
        role_type=skill.role_type,
        role_name=skill.role_name,
        skill_content=skill.skill_content,
        experience_description=skill.experience_description,
        is_primary=skill.is_primary,
        template_version=skill.template_version,
        template_update_available=False,
        word_count=len(skill.skill_content.split()),
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


@router.put(
    "/{skill_id}",
    response_model=RoleSkillResponse,
    summary="Update a role skill",
    description="Update an existing role skill's content or metadata.",
)
async def update_role_skill(
    workspace_id: UUID,
    skill_id: UUID,
    request: UpdateRoleSkillRequest,
    session: DbSession,
    _member_id: WorkspaceMemberId,
    current_user_id: CurrentUserId,
) -> RoleSkillResponse:
    """Update a role skill.

    FR-009: Edit role skill content.
    FR-010: Update skill metadata.
    """
    service = UpdateRoleSkillService(session)

    try:
        skill = await service.execute(
            UpdateRoleSkillPayload(
                user_id=current_user_id,
                skill_id=skill_id,
                workspace_id=workspace_id,
                role_name=request.role_name,
                skill_content=request.skill_content,
                is_primary=request.is_primary,
            )
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        if "not authorized" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        ) from e

    return RoleSkillResponse(
        id=skill.id,
        role_type=skill.role_type,
        role_name=skill.role_name,
        skill_content=skill.skill_content,
        experience_description=skill.experience_description,
        is_primary=skill.is_primary,
        template_version=skill.template_version,
        template_update_available=False,
        word_count=len(skill.skill_content.split()),
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role skill",
    description="Remove a role skill.",
)
async def delete_role_skill(
    workspace_id: UUID,
    skill_id: UUID,
    session: DbSession,
    _member_id: WorkspaceMemberId,
    current_user_id: CurrentUserId,
) -> None:
    """Delete a role skill.

    FR-009: Remove configured role skill.
    """
    service = DeleteRoleSkillService(session)

    try:
        await service.execute(
            DeleteRoleSkillPayload(
                user_id=current_user_id,
                skill_id=skill_id,
                workspace_id=workspace_id,
            )
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        if "not authorized" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        ) from e


@router.post(
    "/generate",
    response_model=GenerateRoleSkillResponse,
    summary="Generate role skill via AI",
    description="Generate role skill content using AI. Returns preview only.",
)
async def generate_role_skill(
    workspace_id: UUID,
    request: GenerateRoleSkillRequest,
    session: DbSession,
    _member_id: WorkspaceMemberId,
    current_user_id: CurrentUserId,
) -> GenerateRoleSkillResponse:
    """Generate role skill content via AI.

    FR-003: AI-powered skill generation.
    FR-004: Experience-based personalization.
    """
    service = GenerateRoleSkillService(session)

    try:
        result = await service.execute(
            GenerateRoleSkillPayload(
                role_type=request.role_type,
                experience_description=request.experience_description,
                role_name=request.role_name,
                workspace_id=workspace_id,
                user_id=current_user_id,
            )
        )
    except SkillGenerationRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return GenerateRoleSkillResponse(
        skill_content=result.skill_content,
        suggested_role_name=result.suggested_role_name,
        word_count=result.word_count,
        generation_model=result.generation_model,
        generation_time_ms=result.generation_time_ms,
    )


@router.post(
    "/{skill_id}/regenerate",
    response_model=RegenerateRoleSkillResponse,
    summary="Regenerate role skill via AI",
    description="Regenerate existing skill with updated experience. Returns preview.",
)
async def regenerate_role_skill(
    workspace_id: UUID,
    skill_id: UUID,
    request: RegenerateRoleSkillRequest,
    session: DbSession,
    _member_id: WorkspaceMemberId,
    current_user_id: CurrentUserId,
) -> RegenerateRoleSkillResponse:
    """Regenerate an existing role skill via AI.

    FR-003: AI-powered skill regeneration.
    FR-015: Update skill with new experience.
    """
    from pilot_space.infrastructure.database.repositories.role_skill_repository import (
        RoleSkillRepository,
    )

    # Verify ownership
    repo = RoleSkillRepository(session)
    skill = await repo.get_by_id(skill_id)
    if skill is None or skill.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role skill not found",
        )
    if skill.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to regenerate this skill",
        )
    if skill.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill does not belong to this workspace",
        )

    previous_content = skill.skill_content
    previous_name = skill.role_name

    service = GenerateRoleSkillService(session)
    try:
        result = await service.execute(
            GenerateRoleSkillPayload(
                role_type=skill.role_type,
                experience_description=request.experience_description,
                role_name=skill.role_name,
                workspace_id=workspace_id,
                user_id=current_user_id,
            )
        )
    except SkillGenerationRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return RegenerateRoleSkillResponse(
        skill_content=result.skill_content,
        suggested_role_name=result.suggested_role_name,
        word_count=result.word_count,
        generation_model=result.generation_model,
        generation_time_ms=result.generation_time_ms,
        previous_skill_content=previous_content,
        previous_role_name=previous_name,
    )


__all__ = ["role_templates_router", "router"]
