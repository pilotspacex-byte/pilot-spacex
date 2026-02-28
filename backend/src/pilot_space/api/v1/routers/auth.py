"""Authentication router for Pilot Space API.

Provides endpoints for OAuth login and user profile management.
Uses Supabase Auth for authentication — OAuth callback and token refresh
are handled client-side by the Supabase JS SDK (RD-002).

Thin HTTP adapter; all business logic delegated to AuthService (DD-064).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from pilot_space.api.v1.dependencies import AuthServiceDep
from pilot_space.api.v1.schemas.auth import (
    LoginRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from pilot_space.application.services.auth import (
    GetLoginUrlPayload,
    GetProfilePayload,
    LogoutPayload,
    UpdateProfilePayload,
)
from pilot_space.dependencies import CurrentUser
from pilot_space.dependencies.auth import SessionDep

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", tags=["auth"])
async def login(
    request: Annotated[LoginRequest, Depends()],
    session: SessionDep,
    service: AuthServiceDep,
) -> dict[str, str]:
    """Initiate OAuth login flow.

    Returns redirect URL for OAuth provider authentication.

    Args:
        request: Login request with provider and redirect URL.
        session: Database session (triggers ContextVar).
        service: Auth service (injected).

    Returns:
        Redirect URL to OAuth provider.
    """
    result = await service.get_login_url(
        GetLoginUrlPayload(
            provider=request.provider,
            redirect_url=request.redirect_url,
        ),
    )
    return {"url": result.url, "provider": result.provider}


@router.get("/me", response_model=UserProfileResponse, tags=["auth"])
async def get_current_user_profile(
    current_user: CurrentUser,
    session: SessionDep,
    service: AuthServiceDep,
) -> UserProfileResponse:
    """Get current authenticated user's profile.

    Args:
        current_user: Current authenticated user from JWT.
        session: Database session (triggers ContextVar).
        service: Auth service (injected).

    Returns:
        User profile information.

    Raises:
        HTTPException: If user not found.
    """
    try:
        result = await service.get_profile(
            GetProfilePayload(user_id=current_user.user_id),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    user = result.user
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        default_sdlc_role=user.default_sdlc_role,
        created_at=user.created_at,
    )


@router.patch("/me", response_model=UserProfileResponse, tags=["auth"])
async def update_current_user_profile(
    request: UserProfileUpdateRequest,
    current_user: CurrentUser,
    session: SessionDep,
    service: AuthServiceDep,
) -> UserProfileResponse:
    """Update current user's profile.

    Args:
        request: Profile update request.
        current_user: Current authenticated user.
        session: Database session (triggers ContextVar).
        service: Auth service (injected).

    Returns:
        Updated user profile.

    Raises:
        HTTPException: If user not found.
    """
    update_data = request.model_dump(exclude_unset=True)

    try:
        result = await service.update_profile(
            UpdateProfilePayload(
                user_id=current_user.user_id,
                full_name=update_data.get("full_name"),
                avatar_url=update_data.get("avatar_url"),
                bio=update_data.get("bio"),
                default_sdlc_role=update_data.get("default_sdlc_role"),
            ),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    user = result.user
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        default_sdlc_role=user.default_sdlc_role,
        created_at=user.created_at,
    )


@router.post("/logout", tags=["auth"])
async def logout(
    current_user: CurrentUser,
    session: SessionDep,
    service: AuthServiceDep,
) -> dict[str, str]:
    """Logout current user.

    Note: With JWT-based auth, server-side logout is a no-op.
    Client should discard the token.

    Args:
        current_user: Current authenticated user.
        session: Database session (triggers ContextVar).
        service: Auth service (injected).

    Returns:
        Success message.
    """
    await service.logout(LogoutPayload(user_id=current_user.user_id))
    return {"message": "Logged out successfully"}


@router.get("/config", tags=["auth"])
async def get_auth_config() -> dict[str, str | None]:
    """Return the active JWT provider configuration.

    Used by the frontend to route token refresh calls to the correct
    auth service (Supabase GoTrue vs AuthCore).

    Returns:
        provider: "supabase" or "authcore"
        authcore_url: AuthCore base URL when provider is "authcore", else null
    """
    from pilot_space.config import get_settings

    settings = get_settings()
    provider = (settings.auth_provider or "supabase").lower().strip()
    authcore_url: str | None = None
    if provider == "authcore":
        authcore_url = getattr(settings, "authcore_url", None)
    return {"provider": provider, "authcore_url": authcore_url}


__all__ = ["router"]
