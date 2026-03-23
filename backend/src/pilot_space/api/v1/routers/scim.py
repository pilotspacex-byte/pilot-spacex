"""SCIM 2.0 router — AUTH-07.

Provides RFC 7644 User resource endpoints for IdP-driven user provisioning.
Endpoint prefix: /scim/v2/{workspace_slug}/

Authentication: SCIM-specific Bearer token (not Supabase JWT).
Token hash stored in workspace.settings["scim_token_hash"].

Supported endpoints:
  GET    /Users                     — list workspace members (paginated)
  POST   /Users                     — provision new user
  GET    /Users/{user_id}           — get single SCIM user
  PUT    /Users/{user_id}           — full replace (PUT)
  PATCH  /Users/{user_id}           — partial update (RFC 7644 PatchOp)
  DELETE /Users/{user_id}           — deprovision (sets is_active=False)
  GET    /ServiceProviderConfig     — SCIM capabilities (no auth required)

SCIM error format:
  {"schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
   "status": "401", "detail": "..."}
"""

from __future__ import annotations

import hashlib
import uuid
from typing import TYPE_CHECKING, Annotated, Any

# scim2_models is an optional dep (excluded on Vercel to stay under 500MB Lambda limit).
# Import here so type annotations work (from __future__ import annotations makes them strings).
# Runtime calls will raise ImportError only if SCIM endpoints are actually invoked.
try:
    from scim2_models import (  # type: ignore[import-untyped]
        ListResponse,
        Meta,
        PatchOp,
        ServiceProviderConfig,
        User,
    )
    from scim2_models.resources.service_provider_config import (  # type: ignore[import-untyped]
        Bulk,
        ChangePassword,
        ETag,
        Filter,
        Patch,
        Sort,
    )
except ImportError:
    pass

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import lazyload

from pilot_space.application.services.scim_service import (
    ScimService,
    ScimUserNotFoundError,
)
from pilot_space.dependencies.auth import SessionDep
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

SCIM_CONTENT_TYPE = "application/scim+json"
SCIM_ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"

router = APIRouter(
    prefix="/scim/v2/{workspace_slug}",
    tags=["scim"],
)


# ---------------------------------------------------------------------------
# SCIM error helpers
# ---------------------------------------------------------------------------


def _scim_error(status_code: int, detail: str) -> JSONResponse:
    """Build a SCIM-compliant error response (RFC 7644 §3.12)."""
    return JSONResponse(
        status_code=status_code,
        content={
            "schemas": [SCIM_ERROR_SCHEMA],
            "status": str(status_code),
            "detail": detail,
        },
        media_type=SCIM_CONTENT_TYPE,
    )


def _member_to_scim_user(member: WorkspaceMember, base_url: str) -> User:  # type: ignore[type-arg]  # pyright: ignore[reportMissingTypeArgument]
    """Convert WorkspaceMember ORM to scim2-models User resource."""
    email = member.user.email if member.user else ""
    display_name = member.user.full_name if member.user else None
    return User(  # pyright: ignore[reportCallIssue,reportPossiblyUnboundVariable]
        id=str(member.user_id),  # pyright: ignore[reportCallIssue]
        user_name=email,  # pyright: ignore[reportCallIssue]
        display_name=display_name,  # pyright: ignore[reportCallIssue]
        active=member.is_active and not member.is_deleted,  # pyright: ignore[reportCallIssue]
        meta=Meta(  # pyright: ignore[reportCallIssue,reportPossiblyUnboundVariable]
            resource_type="User",
            location=f"{base_url}/Users/{member.user_id}",
        ),
    )


# ---------------------------------------------------------------------------
# Workspace lookup helper (shared by dependency and token generate endpoint)
# ---------------------------------------------------------------------------


async def _get_workspace_by_slug(
    workspace_slug: str,
    db: AsyncSession,
) -> Workspace | None:
    """Fetch workspace by slug with scalar columns only."""
    result = await db.execute(
        select(Workspace)
        .options(lazyload("*"))
        .where(
            Workspace.slug == workspace_slug,
            Workspace.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# SCIM bearer token dependency
# ---------------------------------------------------------------------------


async def get_scim_workspace(
    workspace_slug: str,
    request: Request,
    session: SessionDep,
) -> Workspace:
    """Validate SCIM bearer token and return authenticated workspace.

    Args:
        workspace_slug: URL path parameter.
        request: HTTP request (for Authorization header).
        session: DB session (from SessionDep ContextVar).

    Returns:
        Authenticated Workspace object.

    Raises:
        JSONResponse: 401 if token missing/invalid, 404 if workspace not found.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing SCIM bearer token",
        )

    token = auth_header[7:]
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    workspace = await _get_workspace_by_slug(workspace_slug, session)
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_slug}' not found",
        )

    settings = workspace.settings or {}
    stored_hash = settings.get("scim_token_hash")
    if not stored_hash or stored_hash != token_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid SCIM bearer token",
        )

    return workspace


ScimWorkspaceDep = Annotated[Workspace, Depends(get_scim_workspace)]


# ---------------------------------------------------------------------------
# ScimService factory (used in router handlers — not DI-injected)
# ---------------------------------------------------------------------------


def get_scim_service(session: AsyncSession) -> ScimService:
    """Create ScimService with repository instances from session.

    Args:
        session: Database session.

    Returns:
        ScimService instance.
    """
    from pilot_space.infrastructure.database.repositories.user_repository import (
        UserRepository,
    )
    from pilot_space.infrastructure.database.repositories.workspace_repository import (
        WorkspaceRepository,
    )

    return ScimService(
        workspace_repo=WorkspaceRepository(session),
        user_repo=UserRepository(session),
        supabase_admin_client=_get_supabase_admin_client(),
    )


def _get_supabase_admin_client() -> Any:
    """Get Supabase admin client from application settings."""
    try:
        from pilot_space.container import get_container

        container = get_container()
        return container.supabase_auth()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ServiceProviderConfig — no auth required per RFC 7644
# ---------------------------------------------------------------------------


@router.get(
    "/ServiceProviderConfig",
    summary="Get SCIM ServiceProviderConfig",
    response_class=JSONResponse,
)
async def get_service_provider_config(
    workspace_slug: str,
) -> JSONResponse:
    """Return SCIM ServiceProviderConfig (no bearer token required).

    Per RFC 7644 §4, discovery endpoints are public.
    """
    config = ServiceProviderConfig(  # pyright: ignore[reportCallIssue,reportPossiblyUnboundVariable]
        patch=Patch(supported=True),  # pyright: ignore[reportCallIssue,reportPossiblyUnboundVariable]
        bulk=Bulk(supported=False, max_operations=0, max_payload_size=0),  # pyright: ignore[reportCallIssue,reportPossiblyUnboundVariable]
        filter=Filter(supported=True, max_results=100),  # pyright: ignore[reportCallIssue,reportPossiblyUnboundVariable]
        change_password=ChangePassword(supported=False),  # pyright: ignore[reportCallIssue,reportPossiblyUnboundVariable]
        sort=Sort(supported=False),  # pyright: ignore[reportCallIssue,reportPossiblyUnboundVariable]
        etag=ETag(supported=False),  # pyright: ignore[reportCallIssue,reportPossiblyUnboundVariable]
    )
    return JSONResponse(
        content=config.model_dump(exclude_none=True, by_alias=True),
        media_type=SCIM_CONTENT_TYPE,
    )


# ---------------------------------------------------------------------------
# GET /Users — list workspace members
# ---------------------------------------------------------------------------


@router.get(
    "/Users",
    summary="List SCIM Users",
    response_class=JSONResponse,
)
async def list_users(
    workspace_slug: str,
    session: SessionDep,
    workspace: ScimWorkspaceDep,
    start_index: int = Query(default=1, ge=1, alias="startIndex"),
    count: int = Query(default=100, ge=1, le=500),
) -> JSONResponse:
    """List workspace members as SCIM ListResponse.

    Query params follow RFC 7644 §3.4.2.4 pagination:
      startIndex: 1-based (default 1)
      count: max results (default 100, max 500)
    """
    service = get_scim_service(session)
    members, total = await service.list_users(
        workspace_id=workspace.id,
        start_index=start_index,
        count=count,
        db=session,
    )

    base_url = f"/api/v1/scim/v2/{workspace_slug}"
    resources = [_member_to_scim_user(m, base_url) for m in members]

    response = ListResponse[User](  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]
        total_results=total,  # pyright: ignore[reportCallIssue]
        start_index=start_index,  # pyright: ignore[reportCallIssue]
        items_per_page=len(resources),  # pyright: ignore[reportCallIssue]
        resources=resources,  # pyright: ignore[reportCallIssue]
    )
    return JSONResponse(
        content=response.model_dump(exclude_none=True, by_alias=True),
        media_type=SCIM_CONTENT_TYPE,
    )


# ---------------------------------------------------------------------------
# POST /Users — provision user
# ---------------------------------------------------------------------------


@router.post(
    "/Users",
    summary="Provision SCIM User",
    response_class=JSONResponse,
    status_code=status.HTTP_201_CREATED,
)
async def provision_user(
    workspace_slug: str,
    session: SessionDep,
    workspace: ScimWorkspaceDep,
    request: Request,
) -> JSONResponse:
    """Provision a new user (SCIM POST /Users).

    Body: SCIM User resource JSON.
    Returns 201 with the created SCIM User resource.
    """
    body = await request.json()

    # Validate body as SCIM User
    try:
        scim_user = User.model_validate(body)  # pyright: ignore[reportPossiblyUnboundVariable]
    except Exception:
        logger.exception("scim_create_user_invalid_body")
        return _scim_error(
            status.HTTP_400_BAD_REQUEST,
            "Invalid SCIM User body",
        )

    email = scim_user.user_name or ""
    if not email:
        return _scim_error(status.HTTP_400_BAD_REQUEST, "userName is required")

    display_name = scim_user.display_name
    active = scim_user.active if scim_user.active is not None else True

    service = get_scim_service(session)
    member = await service.provision_user(
        workspace_id=workspace.id,
        email=email,
        display_name=display_name,
        active=active,
        db=session,
    )

    base_url = f"/api/v1/scim/v2/{workspace_slug}"
    created_user = _member_to_scim_user(member, base_url)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=created_user.model_dump(exclude_none=True, by_alias=True),
        media_type=SCIM_CONTENT_TYPE,
    )


# ---------------------------------------------------------------------------
# GET /Users/{user_id} — get single user
# ---------------------------------------------------------------------------


@router.get(
    "/Users/{user_id}",
    summary="Get SCIM User",
    response_class=JSONResponse,
)
async def get_user(
    workspace_slug: str,
    user_id: uuid.UUID,
    session: SessionDep,
    workspace: ScimWorkspaceDep,
) -> JSONResponse:
    """Get a single SCIM User resource by id."""
    service = get_scim_service(session)
    member = await service.get_user(
        user_id=user_id,
        workspace_id=workspace.id,
        db=session,
    )
    if member is None:
        return _scim_error(status.HTTP_404_NOT_FOUND, f"User {user_id} not found")

    base_url = f"/api/v1/scim/v2/{workspace_slug}"
    return JSONResponse(
        content=_member_to_scim_user(member, base_url).model_dump(exclude_none=True, by_alias=True),
        media_type=SCIM_CONTENT_TYPE,
    )


# ---------------------------------------------------------------------------
# PUT /Users/{user_id} — full replace
# ---------------------------------------------------------------------------


@router.put(
    "/Users/{user_id}",
    summary="Replace SCIM User",
    response_class=JSONResponse,
)
async def replace_user(
    workspace_slug: str,
    user_id: uuid.UUID,
    session: SessionDep,
    workspace: ScimWorkspaceDep,
    request: Request,
) -> JSONResponse:
    """Full replace (PUT) of a SCIM User resource."""
    body = await request.json()
    try:
        scim_user = User.model_validate(body)  # pyright: ignore[reportPossiblyUnboundVariable]
    except Exception:
        logger.exception("scim_replace_user_invalid_body")
        return _scim_error(status.HTTP_400_BAD_REQUEST, "Invalid SCIM User body")

    email = scim_user.user_name or ""
    if not email:
        return _scim_error(status.HTTP_400_BAD_REQUEST, "userName is required")

    service = get_scim_service(session)
    try:
        member = await service.update_user(
            user_id=user_id,
            workspace_id=workspace.id,
            email=email,
            display_name=scim_user.display_name,
            active=scim_user.active if scim_user.active is not None else True,
            db=session,
        )
    except ScimUserNotFoundError:
        return _scim_error(status.HTTP_404_NOT_FOUND, f"User {user_id} not found")

    base_url = f"/api/v1/scim/v2/{workspace_slug}"
    return JSONResponse(
        content=_member_to_scim_user(member, base_url).model_dump(exclude_none=True, by_alias=True),
        media_type=SCIM_CONTENT_TYPE,
    )


# ---------------------------------------------------------------------------
# PATCH /Users/{user_id} — partial update
# ---------------------------------------------------------------------------


@router.patch(
    "/Users/{user_id}",
    summary="Patch SCIM User",
    response_class=JSONResponse,
)
async def patch_user(
    workspace_slug: str,
    user_id: uuid.UUID,
    session: SessionDep,
    workspace: ScimWorkspaceDep,
    request: Request,
) -> JSONResponse:
    """Apply RFC 7644 PATCH operations to a SCIM User resource."""
    body = await request.json()

    # Parse as PatchOp[User] to validate schemas/Operations keys
    try:
        patch_op = PatchOp[User].model_validate(body)  # type: ignore[index]  # pyright: ignore[reportMissingTypeArgument]
    except Exception:
        logger.exception("scim_patch_user_invalid_body")
        return _scim_error(status.HTTP_400_BAD_REQUEST, "Invalid PatchOp body")

    ops = []
    for operation in patch_op.operations or []:
        ops.append(
            {
                "op": operation.op.value if hasattr(operation.op, "value") else str(operation.op),
                "path": str(operation.path) if operation.path else "",
                "value": operation.value,
            }
        )

    service = get_scim_service(session)
    try:
        member = await service.patch_user(
            user_id=user_id,
            workspace_id=workspace.id,
            patch_ops=ops,
            db=session,
        )
    except ScimUserNotFoundError:
        return _scim_error(status.HTTP_404_NOT_FOUND, f"User {user_id} not found")

    base_url = f"/api/v1/scim/v2/{workspace_slug}"
    return JSONResponse(
        content=_member_to_scim_user(member, base_url).model_dump(exclude_none=True, by_alias=True),
        media_type=SCIM_CONTENT_TYPE,
    )


# ---------------------------------------------------------------------------
# DELETE /Users/{user_id} — deprovision
# ---------------------------------------------------------------------------


@router.delete(
    "/Users/{user_id}",
    summary="Deprovision SCIM User",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def deprovision_user(
    workspace_slug: str,
    user_id: uuid.UUID,
    session: SessionDep,
    workspace: ScimWorkspaceDep,
) -> None:
    """Deprovision a user (sets is_active=False). No data is deleted.

    Returns 204 No Content on success per RFC 7644.
    Raises ScimUserNotFoundError (404) via global handler if user not found.
    """
    service = get_scim_service(session)
    try:
        await service.deprovision_user(
            user_id=user_id,
            workspace_id=workspace.id,
            db=session,
        )
    except ScimUserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        ) from None
