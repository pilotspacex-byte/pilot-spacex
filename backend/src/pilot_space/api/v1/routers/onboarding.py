"""Onboarding API router.

Endpoints for workspace onboarding state management.

T016: Create onboarding router.
T029: Add validate endpoint.
T042: Add guided-note endpoint.
Source: FR-001, FR-002, FR-003, FR-005, FR-011
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from pilot_space.api.v1.schemas.onboarding import (
    GuidedNoteResponse,
    OnboardingResponse,
    OnboardingSteps,
    OnboardingUpdateRequest,
    ValidateKeyRequest,
    ValidateKeyResponse,
)
from pilot_space.application.services.onboarding import (
    CreateGuidedNotePayload,
    CreateGuidedNoteService,
    GetOnboardingService,
    UpdateOnboardingPayload,
    UpdateOnboardingService,
)
from pilot_space.dependencies import DbSession, WorkspaceAdminId

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["onboarding"])


@router.get(
    "/onboarding",
    response_model=OnboardingResponse,
    summary="Get onboarding state",
    description="Get the onboarding progress for a workspace. Only visible to owners/admins.",
)
async def get_onboarding_state(
    workspace_id: UUID,
    session: DbSession,
    _admin_id: WorkspaceAdminId,
) -> OnboardingResponse:
    """Get onboarding state for workspace.

    FR-001: Display onboarding checklist (owner/admin only).
    FR-002: Persist onboarding state per workspace.
    """
    service = GetOnboardingService(session)
    result = await service.execute(workspace_id)

    return OnboardingResponse(
        id=result.id,
        workspace_id=result.workspace_id,
        steps=OnboardingSteps(
            ai_providers=result.steps.ai_providers,
            invite_members=result.steps.invite_members,
            first_note=result.steps.first_note,
            role_setup=result.steps.role_setup,
        ),
        guided_note_id=result.guided_note_id,
        dismissed_at=result.dismissed_at,
        completed_at=result.completed_at,
        completion_percentage=result.completion_percentage,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.patch(
    "/onboarding",
    response_model=OnboardingResponse,
    summary="Update onboarding state",
    description="Update step completion or dismiss the checklist. Only owners/admins.",
)
async def update_onboarding_state(
    workspace_id: UUID,
    request: OnboardingUpdateRequest,
    session: DbSession,
    _admin_id: WorkspaceAdminId,
) -> OnboardingResponse:
    """Update onboarding state for workspace.

    FR-002: Persist onboarding completion state.
    FR-003: Dismiss checklist (collapse to sidebar reminder).
    FR-013: Celebration trigger when all steps complete.
    """
    # Validate request
    if request.step is not None and request.completed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="completed is required when step is provided",
        )

    service = UpdateOnboardingService(session)

    try:
        result = await service.execute(
            UpdateOnboardingPayload(
                workspace_id=workspace_id,
                step=request.step.value if request.step else None,
                completed=request.completed,
                dismissed=request.dismissed,
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return OnboardingResponse(
        id=result.id,
        workspace_id=result.workspace_id,
        steps=OnboardingSteps(
            ai_providers=result.steps.ai_providers,
            invite_members=result.steps.invite_members,
            first_note=result.steps.first_note,
            role_setup=result.steps.role_setup,
        ),
        guided_note_id=result.guided_note_id,
        dismissed_at=result.dismissed_at,
        completed_at=result.completed_at,
        completion_percentage=result.completion_percentage,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.post(
    "/ai-providers/validate",
    response_model=ValidateKeyResponse,
    summary="Validate AI provider key",
    description="Validate an Anthropic API key without saving. Only owners/admins.",
)
async def validate_provider_key(
    _workspace_id: UUID,
    request: ValidateKeyRequest,
    _session: DbSession,
    _admin_id: WorkspaceAdminId,
) -> ValidateKeyResponse:
    """Validate AI provider API key.

    FR-005: Validate Anthropic key via separate endpoint.
    FR-006: Display Anthropic provider status.

    T028/T029: Validates key with Anthropic API (GET /v1/models).
    """
    from pilot_space.ai.providers.key_validator import AIProviderKeyValidator

    # Validate Anthropic key format
    if request.provider.value == "anthropic":
        if not request.api_key.startswith("sk-ant-"):
            return ValidateKeyResponse(
                provider=request.provider,
                valid=False,
                error_message="Invalid key format. Anthropic keys start with 'sk-ant-'",
                models_available=[],
            )

    # Validate with provider
    validator = AIProviderKeyValidator()
    result = await validator.validate_anthropic_key(request.api_key)

    return ValidateKeyResponse(
        provider=request.provider,
        valid=result.valid,
        error_message=result.error_message,
        models_available=result.models_available,
    )


@router.post(
    "/onboarding/guided-note",
    response_model=GuidedNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create guided first note",
    description="Create a guided note with template content. Returns 409 if already exists.",
)
async def create_guided_note(
    workspace_id: UUID,
    session: DbSession,
    user_id: WorkspaceAdminId,
) -> GuidedNoteResponse:
    """Create guided first note for onboarding.

    FR-011: Create guided note with template content.

    Returns existing note if already created.
    """
    service = CreateGuidedNoteService(session)

    try:
        result = await service.execute(
            CreateGuidedNotePayload(
                workspace_id=workspace_id,
                owner_id=user_id,
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Return 409 if note already existed
    if result.already_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Guided note already exists for this workspace",
            headers={"Location": f"/notes/{result.note_id}"},
        )

    return GuidedNoteResponse(
        note_id=result.note_id,
        title=result.title,
        redirect_url=f"/notes/{result.note_id}",
    )


__all__ = ["router"]
