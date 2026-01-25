"""Authentication router for Pilot Space API.

Provides endpoints for OAuth login, token refresh, and user profile management.
Uses Supabase Auth for authentication.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from pilot_space.api.v1.schemas.auth import (
    AuthCallbackRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from pilot_space.config import Settings, get_settings
from pilot_space.dependencies import CurrentUser, DbSession
from pilot_space.infrastructure.database.repositories.user_repository import (
    UserRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_user_repository(session: DbSession) -> UserRepository:
    """Get user repository with session."""
    return UserRepository(session=session)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]


@router.get("/login", tags=["auth"])
async def login(
    request: Annotated[LoginRequest, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """Initiate OAuth login flow.

    Returns redirect URL for OAuth provider authentication.

    Args:
        request: Login request with provider and redirect URL.
        settings: Application settings.

    Returns:
        Redirect URL to OAuth provider.
    """
    # Build Supabase Auth URL
    base_url = settings.supabase_url
    redirect_to = request.redirect_url or f"{settings.cors_origins[0]}/auth/callback"

    auth_url = f"{base_url}/auth/v1/authorize?provider={request.provider}&redirect_to={redirect_to}"

    return {"url": auth_url, "provider": request.provider}


@router.post("/callback", response_model=TokenResponse, tags=["auth"])
async def auth_callback(
    request: AuthCallbackRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Handle OAuth callback and exchange code for tokens.

    Args:
        request: Callback request with authorization code.
        settings: Application settings.

    Returns:
        JWT tokens for authenticated session.

    Raises:
        HTTPException: If token exchange fails.
    """
    # In production, this would call Supabase to exchange the code for tokens
    # For now, return a placeholder response
    # The actual implementation would use httpx to call Supabase Auth API
    logger.info("Processing OAuth callback", extra={"code_length": len(request.code)})

    # TODO: Implement actual token exchange with Supabase Auth
    # This requires httpx call to Supabase /auth/v1/token endpoint
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth callback not yet implemented - use Supabase client-side auth",
    )


@router.post("/refresh", response_model=TokenResponse, tags=["auth"])
async def refresh_token(
    request: RefreshTokenRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Refresh access token using refresh token.

    Args:
        request: Refresh token request.
        settings: Application settings.

    Returns:
        New JWT tokens.

    Raises:
        HTTPException: If refresh fails.
    """
    _ = settings  # Mark as used
    # Placeholder: Implement actual token refresh with Supabase Auth
    logger.info("Processing token refresh")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not yet implemented - use Supabase client-side auth",
    )


@router.get("/me", response_model=UserProfileResponse, tags=["auth"])
async def get_current_user_profile(
    current_user: CurrentUser,
    user_repo: UserRepo,
) -> UserProfileResponse:
    """Get current authenticated user's profile.

    Args:
        current_user: Current authenticated user from JWT.
        user_repo: User repository.

    Returns:
        User profile information.

    Raises:
        HTTPException: If user not found.
    """
    user = await user_repo.get_by_id(current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


@router.patch("/me", response_model=UserProfileResponse, tags=["auth"])
async def update_current_user_profile(
    request: UserProfileUpdateRequest,
    current_user: CurrentUser,
    user_repo: UserRepo,
) -> UserProfileResponse:
    """Update current user's profile.

    Args:
        request: Profile update request.
        current_user: Current authenticated user.
        user_repo: User repository.

    Returns:
        Updated user profile.

    Raises:
        HTTPException: If user not found.
    """
    user = await user_repo.get_by_id(current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(user, key, value)
        user = await user_repo.update(user)

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


@router.post("/logout", tags=["auth"])
async def logout(current_user: CurrentUser) -> dict[str, str]:
    """Logout current user.

    Note: With JWT-based auth, server-side logout is a no-op.
    Client should discard the token.

    Args:
        current_user: Current authenticated user.

    Returns:
        Success message.
    """
    logger.info("User logout", extra={"user_id": str(current_user.user_id)})
    return {"message": "Logged out successfully"}


__all__ = ["router"]
