"""Workspace SCIM settings endpoints — AUTH-07 gap closure.

Provides POST /workspaces/{workspace_slug}/settings/scim-token.
Uses Supabase JWT auth (not SCIM bearer token) — endpoint is OWNER-only.
Token generation delegates to ScimService.generate_scim_token(); the router
is responsible for the final session.commit() (service only calls flush).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from pilot_space.api.v1.routers.scim import get_scim_service
from pilot_space.dependencies.auth import CurrentUser, SessionDep
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.permissions import check_permission
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

workspace_scim_settings_router = APIRouter(tags=["SCIM Settings"])


async def _resolve_workspace_scim(
    workspace_slug: str,
    current_user: CurrentUser,
    session: SessionDep,
) -> Workspace:
    """Resolve workspace by slug and verify caller has settings:manage (OWNER only).

    Args:
        workspace_slug: Workspace slug from the URL path parameter.
        current_user: Authenticated Supabase JWT user.
        session: DB session (required to populate ContextVar per CLAUDE.md Gotcha #1).

    Returns:
        Workspace ORM instance.

    Raises:
        HTTPException: 404 if workspace not found, 403 if not OWNER.
    """
    result = await session.execute(
        select(Workspace).where(
            Workspace.slug == workspace_slug,
            Workspace.is_deleted == False,  # noqa: E712
        )
    )
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    allowed = await check_permission(
        session,
        current_user.user_id,
        workspace.id,
        resource="settings",
        action="manage",
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner permission required",
        )
    return workspace


@workspace_scim_settings_router.post(
    "/{workspace_slug}/settings/scim-token",
    summary="Generate SCIM bearer token (OWNER only)",
    status_code=status.HTTP_200_OK,
)
async def generate_scim_token(
    workspace_slug: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict[str, str]:
    """Generate and store a new SCIM bearer token for a workspace.

    The raw token is returned once — it cannot be retrieved again after this
    response. The SHA-256 hash is stored in workspace.settings["scim_token_hash"].

    Requires settings:manage permission (OWNER only).
    Uses Supabase JWT auth — NOT the SCIM bearer token used by SCIM endpoints.

    Args:
        workspace_slug: Workspace slug.
        session: DB session (required — populates ContextVar, must be committed here).
        current_user: Authenticated user from Supabase JWT.

    Returns:
        {"token": "<raw 43-char URL-safe token>"}
    """
    workspace = await _resolve_workspace_scim(workspace_slug, current_user, session)
    service = get_scim_service(session)
    raw_token = await service.generate_scim_token(workspace_id=workspace.id, db=session)
    # ScimService.generate_scim_token() calls db.flush() only — router owns commit.
    await session.commit()
    logger.info("scim_token_generated", workspace_id=str(workspace.id))
    return {"token": raw_token}


__all__ = ["workspace_scim_settings_router"]
