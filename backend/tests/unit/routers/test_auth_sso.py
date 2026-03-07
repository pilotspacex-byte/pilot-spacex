"""Test scaffolds for SSO authentication router — AUTH-01, AUTH-04, AUTH-06.

These tests define the expected HTTP contract for the /auth/sso endpoints
before implementation begins. All tests are marked xfail(strict=False) so
they are collected by pytest and run, but do not block the suite.

Requirements covered:
  AUTH-01: SAML SSO redirect initiation endpoint
  AUTH-04: SSO-only workspace enforcement at login
  AUTH-06: Revoked session returns 401
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# AUTH-04: SSO-only workspace enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SSO-only enforcement at /auth/login not yet implemented (AUTH-04)",
)
async def test_sso_only_workspace_rejects_password_login() -> None:
    """Password login returns 403 when workspace has sso_required=True.

    Scenario:
        Given workspace has settings["sso_required"] = True
        When POST /auth/login {email, password} is called for that workspace
        Then the response status is 403
        And the error body indicates SSO is required
        And no session token is issued
    """
    raise NotImplementedError(
        "AUTH-04: SSO-only workspace password login rejection not implemented"
    )


# ---------------------------------------------------------------------------
# AUTH-01: SAML SSO initiation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SAML SSO redirect endpoint not yet implemented (AUTH-01)",
)
async def test_saml_sso_endpoint_returns_redirect_url() -> None:
    """GET /auth/sso/saml/initiate returns a redirect URL to the IdP.

    Scenario:
        Given workspace has a valid SAML config (entity_id, sso_url, certificate)
        When GET /auth/sso/saml/initiate?workspace_slug={slug} is called
        Then the response status is 200 (or 302)
        And the body contains a redirect_url pointing to the IdP SSO endpoint
        And the URL contains a SAMLRequest parameter
    """
    raise NotImplementedError("AUTH-01: SAML SSO initiation endpoint not implemented")


# ---------------------------------------------------------------------------
# AUTH-06: Revoked session enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="Revoked session 401 enforcement not yet implemented (AUTH-06)",
)
async def test_revoked_session_returns_401() -> None:
    """Requests with a revoked session token receive 401.

    Scenario:
        Given a valid JWT token for an authenticated user
        And the corresponding WorkspaceSession has revoked_at set (force-terminated)
        When the token is used to call any authenticated endpoint
        Then the response status is 401
        And the response body indicates the session has been revoked
    """
    raise NotImplementedError("AUTH-06: Revoked session 401 enforcement not implemented")
