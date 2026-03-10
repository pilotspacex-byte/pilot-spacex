"""SAML 2.0 SSO and OIDC router — AUTH-01 through AUTH-04.

Endpoints:
  POST /auth/sso/saml/config          — configure SAML IdP (admin)
  GET  /auth/sso/saml/config          — get SAML config (admin)
  GET  /auth/sso/saml/initiate        — start SAML login (no auth)
  POST /auth/sso/saml/callback        — handle SAML assertion (no auth)
  GET  /auth/sso/saml/metadata        — SP metadata XML (no auth)
  POST /auth/sso/oidc/config          — configure OIDC provider (admin)
  GET  /auth/sso/oidc/config          — get OIDC config (admin)
  PATCH /auth/sso/enforcement         — toggle SSO-only enforcement (admin)
  GET  /auth/sso/status               — check SSO availability (no auth)

All HTTP errors use RFC 7807 problem+json format.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, Response

from pilot_space.api.v1.schemas.sso import (
    OidcConfigRequest,
    OidcConfigResponse,
    RoleClaimMappingConfig,
    SamlConfigRequest,
    SamlConfigResponse,
    SsoClaimRoleRequest,
    SsoClaimRoleResponse,
    SsoEnforcementRequest,
    SsoInitiateResponse,
    SsoStatusResponse,
)
from pilot_space.config import get_settings
from pilot_space.dependencies import CurrentUser
from pilot_space.dependencies.auth import SessionDep
from pilot_space.infrastructure.auth.saml_auth import SamlAuthProvider, SamlValidationError
from pilot_space.infrastructure.database.permissions import check_permission
from pilot_space.infrastructure.database.repositories.audit_log_repository import (
    AuditLogRepository,
    write_audit_nonfatal,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(prefix="/auth/sso", tags=["auth-sso"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_sso_service() -> Any:
    """Get SsoService from the DI container (lazy, fail-safe)."""
    try:
        from pilot_space.container import get_container

        return get_container().sso_service()
    except Exception:
        return None


def _get_saml_provider() -> SamlAuthProvider:
    """Build SamlAuthProvider from application settings."""
    settings = get_settings()
    return SamlAuthProvider(
        sp_entity_id=settings.saml_sp_entity_id,
        sp_private_key_pem=settings.saml_sp_private_key.get_secret_value(),
        sp_certificate_pem=settings.saml_sp_cert_pem,
    )


async def _resolve_workspace(workspace_slug: str, session: AsyncSession) -> UUID:
    """Resolve workspace slug (or UUID string) to workspace.id."""
    workspace_repo = WorkspaceRepository(session)
    try:
        as_uuid = UUID(workspace_slug)
        workspace = await workspace_repo.get_by_id_scalar(as_uuid)
    except ValueError:
        workspace = await workspace_repo.get_by_slug_scalar(workspace_slug)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace.id


async def _resolve_and_authorize(
    workspace_slug: str,
    session: AsyncSession,
    user_id: UUID,
) -> UUID:
    """Resolve workspace slug → UUID and verify settings:manage permission.

    Raises:
        HTTPException 404: If workspace not found.
        HTTPException 403: If user lacks settings:manage permission.
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    if not await check_permission(session, user_id, workspace_id, "settings", "manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    return workspace_id


def _saml_config_response(workspace_id: UUID, entity_id: str, sso_url: str) -> SamlConfigResponse:
    """Build SamlConfigResponse with computed metadata and ACS URLs."""
    settings = get_settings()
    base = settings.backend_url.rstrip("/")
    return SamlConfigResponse(
        entity_id=entity_id,
        sso_url=sso_url,
        metadata_url=f"{base}/api/v1/auth/sso/saml/metadata?workspace_id={workspace_id}",
        acs_url=f"{base}/api/v1/auth/sso/saml/callback",
    )


# ---------------------------------------------------------------------------
# SAML configuration endpoints (admin-only)
# ---------------------------------------------------------------------------


@router.post(
    "/saml/config",
    response_model=SamlConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Configure SAML 2.0 IdP for a workspace",
)
async def configure_saml(
    workspace_slug: str,
    body: SamlConfigRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> SamlConfigResponse:
    """Store SAML IdP config. Returns SP metadata and ACS URLs for this workspace."""
    workspace_id = await _resolve_and_authorize(workspace_slug, session, current_user.user_id)

    sso_service = _get_sso_service()
    if sso_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSO service unavailable",
        )

    config = {
        "entity_id": body.entity_id,
        "sso_url": str(body.sso_url),
        "certificate": body.certificate,
        "name_id_format": body.name_id_format,
    }

    try:
        await sso_service.configure_saml(workspace_id, config)
        await session.commit()
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return _saml_config_response(workspace_id, body.entity_id, str(body.sso_url))


@router.get(
    "/saml/config",
    response_model=SamlConfigResponse,
    summary="Get SAML IdP configuration for a workspace",
)
async def get_saml_config(
    workspace_slug: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> SamlConfigResponse:
    """Return stored SAML IdP config. Certificate is NOT returned (key exfiltration guard)."""
    workspace_id = await _resolve_and_authorize(workspace_slug, session, current_user.user_id)

    sso_service = _get_sso_service()
    if sso_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO service unavailable"
        )

    config = await sso_service.get_saml_config(workspace_id)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SAML not configured for this workspace"
        )

    return _saml_config_response(workspace_id, config["entity_id"], config["sso_url"])


# ---------------------------------------------------------------------------
# SAML login flow (no auth required)
# ---------------------------------------------------------------------------


@router.get(
    "/saml/initiate",
    response_model=SsoInitiateResponse,
    summary="Initiate SP-initiated SAML login — returns redirect URL",
)
async def initiate_saml_login(
    request: Request,
    workspace_id: UUID,
    session: SessionDep,
    return_to: str = Query(default="/", description="URL to redirect to after login"),
) -> SsoInitiateResponse:
    """Return the IdP redirect URL for SP-initiated SAML login.

    No authentication required — called before the user is logged in.
    """
    sso_service = _get_sso_service()
    if sso_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO service unavailable"
        )

    idp_config = await sso_service.get_saml_config(workspace_id)
    if not idp_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML not configured for this workspace",
        )

    try:
        provider = _get_saml_provider()
        redirect_url = provider.get_login_url(request, idp_config, return_to)
    except SamlValidationError as exc:
        logger.warning("saml_initiate_failed", workspace_id=str(workspace_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build SAML login URL",
        ) from exc

    return SsoInitiateResponse(redirect_url=redirect_url)


@router.post(
    "/saml/callback",
    summary="Handle SAML assertion from IdP",
)
async def saml_callback(
    request: Request,
    workspace_id: UUID,
    session: SessionDep,
    SAMLResponse: str = Form(...),
    RelayState: str = Form(default=""),
) -> Response:
    """Validate SAML assertion from IdP, provision user, redirect to frontend with token_hash.

    Raises:
        401: If assertion is invalid or expired.
    """
    sso_service = _get_sso_service()
    if sso_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO service unavailable"
        )
    idp_config = await sso_service.get_saml_config(workspace_id)
    if not idp_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="SAML not configured for this workspace"
        )
    post_data = {"SAMLResponse": SAMLResponse, "RelayState": RelayState}
    try:
        provider = _get_saml_provider()
        result = provider.process_response(request, post_data, idp_config)
    except SamlValidationError as exc:
        logger.warning("saml_callback_invalid", workspace_id=str(workspace_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"SAML assertion validation failed: {exc}",
        ) from exc
    # Extract email from SAML attributes or name_id
    name_id: str = result.get("name_id") or ""
    attributes: dict[str, list[str]] = result.get("attributes") or {}
    email_attrs = (
        attributes.get("email") or attributes.get("emailAddress") or attributes.get("Email") or []
    )
    email = (email_attrs[0] if email_attrs else None) or name_id
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="SAML assertion missing email attribute"
        )
    display_name_attrs = (
        attributes.get("displayName") or attributes.get("name") or attributes.get("cn") or []
    )
    display_name = display_name_attrs[0] if display_name_attrs else email.split("@")[0]
    try:
        user_info = await sso_service.provision_saml_user(
            email=email,
            display_name=display_name,
            workspace_id=workspace_id,
        )
        await session.commit()
    except RuntimeError as exc:
        logger.exception("saml_user_provision_failed", email=email, workspace_id=str(workspace_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to provision user"
        ) from exc
    _ip = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or None
    try:
        await set_rls_context(session, UUID(str(user_info["user_id"])), workspace_id)
        await write_audit_nonfatal(
            AuditLogRepository(session),
            workspace_id=workspace_id,
            actor_id=UUID(str(user_info["user_id"])),
            action="user.login",
            resource_type="user",
            resource_id=UUID(str(user_info["user_id"])),
            payload={"method": "saml", "is_new": user_info.get("is_new", False)},
            ip_address=_ip,
        )
    except Exception:
        logger.warning("saml_callback: audit write failed for user %s", user_info["user_id"])
    # Redirect browser to frontend SAML callback page with token_hash for verifyOtp.
    # token_hash is a Supabase-generated hex value; validate format before using.
    raw_token_hash = str(user_info.get("token_hash", ""))
    token_hash = raw_token_hash if re.fullmatch(r"[0-9a-fA-F]{1,256}", raw_token_hash) else ""
    settings = get_settings()
    frontend_base = settings.frontend_url.rstrip("/")
    safe_params = urlencode({"token_hash": token_hash, "workspace_id": str(workspace_id)})
    return RedirectResponse(
        url=f"{frontend_base}/auth/saml-callback?{safe_params}", status_code=302
    )


@router.get(
    "/saml/metadata",
    summary="SP metadata XML for IdP registration",
)
async def get_sp_metadata(
    request: Request,
    workspace_id: UUID,
    session: SessionDep,
) -> Response:
    """Return the SP metadata XML for this workspace's IdP configuration.

    No auth required — IdPs fetch this to configure trust.
    """
    sso_service = _get_sso_service()
    if sso_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO service unavailable"
        )

    idp_config = await sso_service.get_saml_config(workspace_id)
    if not idp_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SAML not configured for this workspace"
        )

    try:
        provider = _get_saml_provider()
        metadata_xml = provider.get_metadata_xml(idp_config)
    except SamlValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate SP metadata",
        ) from exc

    return Response(content=metadata_xml, media_type="application/xml")


# ---------------------------------------------------------------------------
# OIDC configuration endpoints (admin-only)
# ---------------------------------------------------------------------------


@router.post(
    "/oidc/config",
    response_model=OidcConfigResponse,
    summary="Configure OIDC provider for a workspace",
)
async def configure_oidc(
    workspace_slug: str,
    body: OidcConfigRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> OidcConfigResponse:
    """Store OIDC provider configuration for a workspace."""
    workspace_id = await _resolve_and_authorize(workspace_slug, session, current_user.user_id)

    sso_service = _get_sso_service()
    if sso_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO service unavailable"
        )

    config = {
        "provider": body.provider,
        "client_id": body.client_id,
        "client_secret": body.client_secret,
        "issuer_url": str(body.issuer_url) if body.issuer_url else None,
    }

    try:
        await sso_service.configure_oidc(workspace_id, config)
        await session.commit()
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return OidcConfigResponse(
        provider=body.provider,
        client_id=body.client_id,
        issuer_url=str(body.issuer_url) if body.issuer_url else None,
        enabled=True,
    )


@router.get(
    "/oidc/config",
    response_model=OidcConfigResponse,
    summary="Get OIDC provider configuration for a workspace",
)
async def get_oidc_config(
    workspace_slug: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> OidcConfigResponse:
    """Return stored OIDC config — client_secret is NOT returned."""
    workspace_id = await _resolve_and_authorize(workspace_slug, session, current_user.user_id)

    sso_service = _get_sso_service()
    if sso_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO service unavailable"
        )

    config = await sso_service.get_oidc_config(workspace_id)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OIDC not configured for this workspace"
        )

    return OidcConfigResponse(
        provider=config["provider"],
        client_id=config["client_id"],
        issuer_url=config.get("issuer_url"),
        enabled=True,
    )


# ---------------------------------------------------------------------------
# SSO enforcement (admin-only)
# ---------------------------------------------------------------------------


@router.patch(
    "/enforcement",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Toggle SSO-only enforcement for a workspace",
)
async def set_sso_enforcement(
    workspace_slug: str,
    body: SsoEnforcementRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    """Enable or disable SSO-only enforcement (AUTH-04)."""
    workspace_id = await _resolve_and_authorize(workspace_slug, session, current_user.user_id)

    sso_service = _get_sso_service()
    if sso_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO service unavailable"
        )

    try:
        await sso_service.set_sso_required(workspace_id, required=body.sso_required)
        await session.commit()
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# SSO status — NO AUTH REQUIRED
# ---------------------------------------------------------------------------


@router.get(
    "/status",
    response_model=SsoStatusResponse,
    summary="Check SSO availability for a workspace (no auth required)",
    description=(
        "Returns SSO configuration status for a workspace. "
        "Called by the login page before the user authenticates to decide "
        "whether to show an 'SSO Login' button. "
        "If workspace_id is unknown, returns all-false gracefully (no 404)."
    ),
)
async def get_sso_status(
    workspace_id: UUID,
    session: SessionDep,
) -> SsoStatusResponse:
    """Return SSO status for a workspace. No authentication required.

    Gracefully returns all-false if workspace does not exist — login page
    should degrade gracefully rather than show a broken error state.
    """
    sso_service = _get_sso_service()
    if sso_service is None:
        return SsoStatusResponse(
            has_saml=False,
            has_oidc=False,
            sso_required=False,
            oidc_provider=None,
        )

    status_dict = await sso_service.get_sso_status(workspace_id)

    return SsoStatusResponse(
        has_saml=status_dict["has_saml"],
        has_oidc=status_dict["has_oidc"],
        sso_required=status_dict["sso_required"],
        oidc_provider=status_dict["oidc_provider"],
    )


# ---------------------------------------------------------------------------
# SSO enforcement check — AUTH-04
# ---------------------------------------------------------------------------


@router.get(
    "/check-login",
    summary="Check whether password login is allowed for a workspace (no auth required)",
    description=(
        "Returns whether email/password login is allowed for a workspace. "
        "Returns 403 with a clear message if the workspace requires SSO-only login. "
        "No authentication required — called by the login page before submitting credentials."
    ),
)
async def check_sso_login_allowed(
    workspace_id: UUID,
    session: SessionDep,
) -> dict[str, bool]:
    """Return whether password login is allowed for this workspace.

    If the workspace has sso_required=True, raises 403 with a clear SSO enforcement message.
    This endpoint is called by the login form BEFORE submitting email+password credentials,
    so the frontend can redirect to SSO instead of showing password fields.

    Args:
        workspace_id: Target workspace UUID (query param).
        session: DB session.

    Returns:
        {"password_login_allowed": True} if password login is permitted.

    Raises:
        403: If workspace requires SSO login.
    """
    sso_service = _get_sso_service()
    if sso_service is None:
        # Service unavailable — fail open (allow password login) to avoid lockouts
        return {"password_login_allowed": True}

    sso_status = await sso_service.get_sso_status(workspace_id)
    if sso_status.get("sso_required"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This workspace requires SSO login. Use your identity provider account.",
        )

    return {"password_login_allowed": True}


# ---------------------------------------------------------------------------
# Role claim mapping (AUTH-03)
# ---------------------------------------------------------------------------


@router.post(
    "/role-mapping",
    status_code=status.HTTP_200_OK,
    summary="Configure IdP role-claim → workspace role mapping (admin-only)",
)
async def configure_role_claim_mapping(
    workspace_slug: str,
    body: RoleClaimMappingConfig,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict[str, str]:
    """Store or update IdP role-claim → workspace role mapping."""
    workspace_id = await _resolve_and_authorize(workspace_slug, session, current_user.user_id)

    sso_service = _get_sso_service()
    if sso_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO service unavailable"
        )

    try:
        await sso_service.configure_role_claim_mapping(
            workspace_id,
            claim_key=body.claim_key,
            mappings=body.mappings,
        )
        await session.commit()
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"status": "ok"}


@router.get(
    "/role-mapping",
    summary="Get the current role claim mapping configuration (admin-only)",
)
async def get_role_claim_mapping(
    workspace_slug: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> RoleClaimMappingConfig | None:
    """Return current role claim mapping config, or None if not configured."""
    workspace_id = await _resolve_and_authorize(workspace_slug, session, current_user.user_id)

    sso_service = _get_sso_service()
    if sso_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO service unavailable"
        )

    config = await sso_service.get_role_claim_mapping(workspace_id)
    if config is None:
        return None

    return RoleClaimMappingConfig(
        claim_key=config["claim_key"],
        mappings=config["mappings"],
    )


@router.post(
    "/claim-role",
    response_model=SsoClaimRoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply SSO-mapped role from JWT claims after login (authenticated)",
)
async def claim_sso_role(
    body: SsoClaimRoleRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> SsoClaimRoleResponse:
    """Apply the workspace role mapped from the user's SSO JWT claims.

    Called by the frontend immediately after OIDC/SAML login to apply the
    correct workspace role from the IdP's group/role claims.

    Server-side validated: frontend sends raw claims; backend applies mapping.
    Unmapped claims always default to "member".

    Args:
        body: workspace_id + jwt_claims extracted from the Supabase JWT.
        session: DB session (required for DI ContextVar).
        current_user: Authenticated user from Supabase JWT.

    Returns:
        Applied role name.

    Raises:
        404: If workspace or membership not found.
        503: If SSO service unavailable.
    """
    sso_service = _get_sso_service()
    if sso_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO service unavailable"
        )

    try:
        member = await sso_service.apply_sso_role(
            user_id=current_user.user_id,
            workspace_id=body.workspace_id,
            jwt_claims=body.jwt_claims,
        )
        await session.commit()
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    logger.info(
        "sso_claim_role_applied",
        user_id=str(current_user.user_id),
        workspace_id=str(body.workspace_id),
        role=str(member.role.value if hasattr(member.role, "value") else member.role),
    )

    role_str = (
        member.role.value.lower() if hasattr(member.role, "value") else str(member.role).lower()
    )
    return SsoClaimRoleResponse(role=role_str)
