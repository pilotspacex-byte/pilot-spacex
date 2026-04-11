"""Authentication router for Pilot Space API.

Provides endpoints for OAuth login and user profile management.
Uses Supabase Auth for authentication — OAuth callback and token refresh
are handled client-side by the Supabase JS SDK (RD-002).

Thin HTTP adapter; all business logic delegated to AuthService (DD-064).
"""

from __future__ import annotations

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import Field
from sqlalchemy import select

from pilot_space.api.v1.dependencies import AuthServiceDep
from pilot_space.api.v1.dependencies_pilot import ValidateAPIKeyServiceDep
from pilot_space.api.v1.repository_deps import (
    InvitationRepositoryDep,
    UserRepositoryDep,
    WorkspaceRepositoryDep,
)
from pilot_space.api.v1.schemas.auth import (
    AiSettingsSchema,
    LoginRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    WorkspaceMembershipInfo,
)
from pilot_space.api.v1.schemas.base import BaseSchema
from pilot_space.application.services.auth import (
    UNSET,
    GetLoginUrlPayload,
    GetProfilePayload,
    LogoutPayload,
    UpdateProfilePayload,
    ValidateAPIKeyPayload,
)
from pilot_space.application.services.workspace_invitation import (
    AcceptInvitationPayload,
    WorkspaceInvitationService,
)
from pilot_space.dependencies import CurrentUser
from pilot_space.dependencies.auth import SessionDep, SyncedUserId
from pilot_space.domain.exceptions import ConflictError, NotFoundError
from pilot_space.infrastructure.database.models.workspace_invitation import InvitationStatus
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember
from pilot_space.infrastructure.supabase_client import get_supabase_client

router = APIRouter(prefix="/auth", tags=["auth"])


class CompleteSignupRequest(BaseSchema):
    """Request body for POST /auth/complete-signup."""

    invitation_id: UUID
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, description="Password for the new account")


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
    result = await service.get_profile(
        GetProfilePayload(user_id=current_user.user_id),
    )

    # Fetch workspace memberships for the current user inline.
    # Querying workspace_members directly avoids coupling the auth service to
    # workspace domain logic, consistent with how ai_settings is fetched separately.
    memberships_result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == UUID(str(current_user.user_id)),
            WorkspaceMember.is_deleted == False,  # noqa: E712
        )
    )
    memberships = memberships_result.scalars().all()

    user = result.user
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        default_sdlc_role=user.default_sdlc_role,
        ai_settings=AiSettingsSchema.model_validate(user.ai_settings) if user.ai_settings else None,
        created_at=user.created_at,
        workspace_memberships=[
            WorkspaceMembershipInfo(
                workspace_id=m.workspace_id,
                role=m.role.value.lower(),
            )
            for m in memberships
        ],
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

    result = await service.update_profile(
        UpdateProfilePayload(
            user_id=current_user.user_id,
            full_name=update_data.get("full_name"),
            avatar_url=update_data.get("avatar_url"),
            bio=update_data.get("bio"),
            default_sdlc_role=update_data.get("default_sdlc_role"),
            ai_settings=update_data.get("ai_settings", UNSET),
        ),
    )

    user = result.user
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        default_sdlc_role=user.default_sdlc_role,
        ai_settings=AiSettingsSchema.model_validate(user.ai_settings) if user.ai_settings else None,
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


_VALIDATE_KEY_RATE_LIMIT = 20  # max requests per window
_VALIDATE_KEY_RATE_WINDOW = 60  # seconds


async def _check_validate_key_rate_limit(request: Request, response: Response) -> None:
    """Enforce IP-based rate limit on the validate-key endpoint via Redis.

    Fail-open on Redis outage to avoid blocking legitimate requests.

    Args:
        request: Incoming request (used to read client IP).
        response: Response object (used to set Retry-After header on 429).

    Raises:
        HTTPException 429: If the rate limit has been exceeded.
    """
    try:
        from pilot_space.dependencies.ai import get_redis_client

        redis = await get_redis_client(request)
        client_ip = request.client.host if request.client else "unknown"
        rate_key = f"validate_key_rl:{client_ip}"
        count: int = (await redis.incr(rate_key)) or 0
        if count == 1:
            await redis.expire(rate_key, _VALIDATE_KEY_RATE_WINDOW)
        if count > _VALIDATE_KEY_RATE_LIMIT:
            response.headers["Retry-After"] = str(_VALIDATE_KEY_RATE_WINDOW)
            _raise_rate_limited()
    except HTTPException:
        raise
    except Exception:
        pass  # Fail open — do not block legitimate requests on Redis outage


def _raise_rate_limited() -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded. Try again later.",
    )


@router.post(
    "/validate-key",
    summary="Validate a Pilot CLI API key",
    description=(
        "Used by the `pilot` CLI to verify the configured API key before use. "
        "Reads `Authorization: Bearer <key>` from the request header. "
        "Does NOT require Supabase JWT — the API key IS the authentication mechanism. "
        "Rate-limited to 20 requests per 60 seconds per IP."
    ),
    status_code=status.HTTP_200_OK,
)
async def validate_api_key(
    request: Request,
    response: Response,
    _session: SessionDep,
    service: ValidateAPIKeyServiceDep,
) -> dict[str, str]:
    """POST /api/v1/auth/validate-key

    Validates a CLI API key supplied via Bearer token header.
    Returns workspace_slug on success; 401 on invalid or expired key.

    Rate limited by IP address (20 req / 60s) to prevent brute-force attacks.
    A fixed 50ms delay is applied on both success and failure paths to make
    timing-based oracle attacks infeasible.

    Args:
        request: Incoming HTTP request (used to read Authorization header and client IP).
        response: FastAPI response (used to set Retry-After header on 429).
        service: ValidateAPIKeyService (injected via DI container).
        _session: Database session — establishes ContextVar for repositories.

    Returns:
        JSON body with ``workspace_slug`` on success.

    Raises:
        HTTPException 401: Authorization header missing, malformed, or invalid/expired key.
        HTTPException 429: Rate limit exceeded.
    """
    # IP-based rate limiting via Redis (fail-open on Redis outage)
    await _check_validate_key_rate_limit(request, response)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        await asyncio.sleep(0.05)  # constant-time response
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer <api-key>",
        )

    raw_key = auth_header[len("Bearer ") :]
    try:
        result = await service.execute(ValidateAPIKeyPayload(raw_key=raw_key), _session)
    finally:
        await asyncio.sleep(0.05)  # constant-time regardless of success/failure
    return {"workspace_slug": result.workspace_slug}


@router.post(
    "/complete-signup",
    tags=["auth", "invitations"],
    status_code=status.HTTP_200_OK,
)
async def complete_signup(
    request: CompleteSignupRequest,
    session: SessionDep,
    synced_user_id: SyncedUserId,
    service: AuthServiceDep,
    invitation_repo: InvitationRepositoryDep,
    workspace_repo: WorkspaceRepositoryDep,
    user_repo: UserRepositoryDep,
) -> dict[str, str]:
    """Complete signup for a new user arriving via workspace invitation.

    Atomically updates the user's full name, sets password via Supabase Admin API,
    and accepts the workspace invitation. For new users, the invitation is
    auto-accepted by SyncedUserId before this body executes. For existing users
    whose invitation is still PENDING, explicit acceptance is performed here.

    Returns:
        workspace_slug: Slug to redirect to after completion.

    Raises:
        NotFoundError (404): Invitation not found or workspace not found.
        ConflictError (409): Invitation already accepted or cancelled.
    """
    # Preflight: validate invitation exists and is still pending before touching external systems
    invitation = await invitation_repo.get_by_id(request.invitation_id)
    if invitation is None:
        raise NotFoundError("Invitation not found")
    if invitation.status not in (InvitationStatus.PENDING, InvitationStatus.ACCEPTED):
        raise ConflictError("Invitation has been cancelled or expired")

    await service.update_profile(
        UpdateProfilePayload(
            user_id=synced_user_id,
            full_name=request.full_name,
        )
    )

    supabase_client = await get_supabase_client()
    await supabase_client.auth.admin.update_user_by_id(
        str(synced_user_id),
        {"password": request.password},
    )

    if invitation.status == InvitationStatus.PENDING:
        svc = WorkspaceInvitationService(
            workspace_repo=workspace_repo,
            invitation_repo=invitation_repo,
            user_repo=user_repo,
        )
        result = await svc.accept_invitation(
            AcceptInvitationPayload(
                invitation_id=request.invitation_id,
                user_id=synced_user_id,
            )
        )
        workspace_slug = result.workspace_slug
    else:
        workspace = await workspace_repo.get_by_id(invitation.workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace not found")
        workspace_slug = workspace.slug

    await session.commit()

    return {"workspace_slug": workspace_slug}


__all__ = ["router"]
