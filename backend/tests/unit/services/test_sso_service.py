"""Test scaffolds for SSOService — AUTH-01 through AUTH-04.

These tests define the expected contract for the SSO service before
implementation begins. All tests are marked xfail(strict=False) so
they are collected by pytest and run, but do not block the suite.

Requirements covered:
  AUTH-01: SAML 2.0 SSO configuration and assertion validation
  AUTH-02: OIDC SSO configuration
  AUTH-03: Role claim mapping from IdP assertions
  AUTH-04: SSO-only enforcement per workspace
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# AUTH-01: SAML 2.0
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SSOService.configure_saml not yet implemented (AUTH-01)",
)
async def test_saml_config_stored_and_retrieved() -> None:
    """SAML config is persisted to workspace.settings and can be retrieved.

    Scenario:
        Given a workspace admin stores a SAML config
          (entity_id, sso_url, certificate)
        When the config is retrieved via SSOService.get_saml_config(workspace_id)
        Then the returned config matches the stored values
    """
    raise NotImplementedError("AUTH-01: SSOService.configure_saml not implemented")


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SSOService.validate_saml_assertion not yet implemented (AUTH-01)",
)
async def test_saml_invalid_assertion_rejected() -> None:
    """SAML assertions with invalid signatures are rejected with AuthError.

    Scenario:
        Given a SAML assertion with a tampered or missing signature
        When SSOService.validate_saml_assertion(assertion) is called
        Then an AuthenticationError is raised
        And no session is created
    """
    raise NotImplementedError("AUTH-01: SSOService.validate_saml_assertion not implemented")


# ---------------------------------------------------------------------------
# AUTH-02: OIDC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SSOService.configure_oidc not yet implemented (AUTH-02)",
)
async def test_oidc_config_stored_and_retrieved() -> None:
    """OIDC config is persisted to workspace.settings and can be retrieved.

    Scenario:
        Given a workspace admin stores an OIDC config
          (client_id, client_secret, discovery_url)
        When the config is retrieved via SSOService.get_oidc_config(workspace_id)
        Then the returned config matches the stored values
        And client_secret is not stored in plaintext
    """
    raise NotImplementedError("AUTH-02: SSOService.configure_oidc not implemented")


# ---------------------------------------------------------------------------
# AUTH-03: Role claim mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SSOService.map_role_from_claims not yet implemented (AUTH-03)",
)
async def test_role_claim_mapping_applies_correct_role() -> None:
    """IdP role claims are mapped to WorkspaceRole according to mapping config.

    Scenario:
        Given workspace has role_claim_mapping = {"engineering": "MEMBER", "devops": "ADMIN"}
        When an IdP assertion includes role claim "devops"
        Then SSOService.map_role_from_claims returns WorkspaceRole.ADMIN
    """
    raise NotImplementedError("AUTH-03: SSOService.map_role_from_claims not implemented")


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SSOService.map_role_from_claims default not yet implemented (AUTH-03)",
)
async def test_unmapped_claim_defaults_to_member() -> None:
    """An IdP role claim with no mapping defaults to WorkspaceRole.MEMBER.

    Scenario:
        Given workspace has role_claim_mapping = {"admin": "ADMIN"}
        When an IdP assertion includes role claim "intern" (not in mapping)
        Then SSOService.map_role_from_claims returns WorkspaceRole.MEMBER
    """
    raise NotImplementedError("AUTH-03: Default role fallback for unmapped claims not implemented")


# ---------------------------------------------------------------------------
# AUTH-04: SSO-only enforcement flag
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SSOService.set_sso_required not yet implemented (AUTH-04)",
)
async def test_sso_only_flag_stored_in_workspace_settings() -> None:
    """Setting sso_required=True is persisted in workspace.settings JSONB.

    Scenario:
        Given a workspace admin calls SSOService.set_sso_required(workspace_id, True)
        When workspace.settings is reloaded from the database
        Then workspace.settings["sso_required"] is True
    """
    raise NotImplementedError("AUTH-04: SSOService.set_sso_required not implemented")
