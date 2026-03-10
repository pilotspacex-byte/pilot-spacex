"""Pydantic schemas for SSO configuration endpoints.

Covers SAML 2.0 (AUTH-01), OIDC (AUTH-02), role-claim mapping (AUTH-03),
and SSO enforcement (AUTH-04).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class SamlConfigRequest(BaseModel):
    """Request body for configuring SAML 2.0 IdP settings."""

    entity_id: str
    sso_url: HttpUrl
    certificate: str  # PEM cert content (IdP cert, no header/footer required)
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"


class SamlConfigResponse(BaseModel):
    """Response after SAML configuration is stored."""

    entity_id: str
    sso_url: str
    metadata_url: str  # e.g. /api/v1/auth/sso/saml/metadata?workspace_id=X
    acs_url: str  # Assertion Consumer Service URL


class OidcConfigRequest(BaseModel):
    """Request body for configuring OIDC provider settings."""

    provider: str  # "google" | "azure" | "okta"
    client_id: str
    client_secret: str
    issuer_url: HttpUrl | None = None  # required for okta/azure


class OidcConfigResponse(BaseModel):
    """Response after OIDC configuration is stored."""

    provider: str
    client_id: str
    issuer_url: str | None
    enabled: bool


class SsoInitiateResponse(BaseModel):
    """Response containing the IdP redirect URL to initiate SSO login."""

    redirect_url: str


class SsoStatusResponse(BaseModel):
    """SSO status for a workspace — returned without authentication.

    Used by the login page to determine whether to show an 'SSO Login' button.
    """

    has_saml: bool
    has_oidc: bool
    sso_required: bool
    oidc_provider: str | None  # e.g. "google", "azure", "okta" or None


class RoleClaimMappingRequest(BaseModel):
    """Request body for configuring IdP role-claim → workspace role mappings."""

    claim_key: str  # e.g. "groups"
    mappings: list[dict[str, str]]  # [{"claim_value": "eng-leads", "role": "admin"}]


class SsoEnforcementRequest(BaseModel):
    """Request body for toggling SSO-only enforcement."""

    sso_required: bool


class SsoClaimRoleRequest(BaseModel):
    """Request body for applying SSO role from JWT claims.

    Frontend extracts JWT claims after OIDC/SAML login and sends them here
    for server-side validated role mapping.
    """

    workspace_id: UUID
    jwt_claims: dict[str, Any]  # claims extracted from Supabase JWT by frontend


class RoleClaimMappingConfig(BaseModel):
    """Request body for configuring IdP group-claim → workspace role mappings."""

    claim_key: str  # e.g. "groups"
    mappings: list[dict[str, str]]  # [{"claim_value": "eng-leads", "role": "admin"}]


class SsoClaimRoleResponse(BaseModel):
    """Response after SSO role has been applied."""

    role: str  # applied role name, e.g. "admin", "member"
