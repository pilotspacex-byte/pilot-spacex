"""Tests for SSO authentication router — AUTH-01 through AUTH-04.

Tests cover:
  - GET /auth/sso/status: returns SSO availability for a workspace (no auth)
  - Graceful degradation when SSO service unavailable
  - Correct reflection of SAML/OIDC/enforcement configuration
  - POST /auth/sso/claim-role: applies mapped role from JWT claims
  - SSO-only enforcement: sso_required=True causes 403 on check-login
  - SAML initiate returns redirect_url
  - SAML callback rejects tampered assertion
  - Revoked session returns 401
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_sso_status(
    *,
    has_saml: bool = False,
    has_oidc: bool = False,
    sso_required: bool = False,
    oidc_provider: str | None = None,
) -> dict:
    return {
        "has_saml": has_saml,
        "has_oidc": has_oidc,
        "sso_required": sso_required,
        "oidc_provider": oidc_provider,
    }


@pytest.mark.asyncio
async def test_sso_status_returns_all_false_when_service_unavailable() -> None:
    """GET /auth/sso/status returns all-false when SsoService cannot be instantiated.

    Scenario:
        Given the DI container fails to provide SsoService (_get_sso_service returns None)
        When GET /auth/sso/status?workspace_id={id} is called
        Then the response status is 200
        And has_saml, has_oidc, sso_required are all False
        And oidc_provider is None
    """
    from pilot_space.api.v1.routers.auth_sso import get_sso_status
    from pilot_space.api.v1.schemas.sso import SsoStatusResponse

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()

    with patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=None):
        result = await get_sso_status(workspace_id=workspace_id, session=mock_session)

    assert isinstance(result, SsoStatusResponse)
    assert result.has_saml is False
    assert result.has_oidc is False
    assert result.sso_required is False
    assert result.oidc_provider is None


@pytest.mark.asyncio
async def test_sso_status_returns_has_saml_when_configured() -> None:
    """GET /auth/sso/status returns has_saml=True when SAML is configured.

    Scenario:
        Given workspace has a valid SAML configuration stored
        When GET /auth/sso/status?workspace_id={id} is called
        Then the response has has_saml=True
        And other flags reflect actual configuration
    """
    from pilot_space.api.v1.routers.auth_sso import get_sso_status
    from pilot_space.api.v1.schemas.sso import SsoStatusResponse

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()

    mock_service = MagicMock()
    mock_service.get_sso_status = AsyncMock(return_value=_make_sso_status(has_saml=True))

    with patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service):
        result = await get_sso_status(workspace_id=workspace_id, session=mock_session)

    mock_service.get_sso_status.assert_called_once_with(workspace_id)
    assert isinstance(result, SsoStatusResponse)
    assert result.has_saml is True
    assert result.has_oidc is False
    assert result.sso_required is False


@pytest.mark.asyncio
async def test_sso_status_returns_sso_required_when_enforcement_enabled() -> None:
    """GET /auth/sso/status reflects sso_required=True when enforcement is active.

    Scenario:
        Given workspace has SSO-only enforcement enabled
        When GET /auth/sso/status?workspace_id={id} is called
        Then the response has sso_required=True
    """
    from pilot_space.api.v1.routers.auth_sso import get_sso_status
    from pilot_space.api.v1.schemas.sso import SsoStatusResponse

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()

    mock_service = MagicMock()
    mock_service.get_sso_status = AsyncMock(
        return_value=_make_sso_status(has_saml=True, sso_required=True)
    )

    with patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service):
        result = await get_sso_status(workspace_id=workspace_id, session=mock_session)

    assert isinstance(result, SsoStatusResponse)
    assert result.sso_required is True


@pytest.mark.asyncio
async def test_sso_status_returns_oidc_provider_when_oidc_configured() -> None:
    """GET /auth/sso/status returns oidc_provider name when OIDC is configured.

    Scenario:
        Given workspace has OIDC configured with provider="google"
        When GET /auth/sso/status?workspace_id={id} is called
        Then the response has has_oidc=True and oidc_provider="google"
    """
    from pilot_space.api.v1.routers.auth_sso import get_sso_status
    from pilot_space.api.v1.schemas.sso import SsoStatusResponse

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()

    mock_service = MagicMock()
    mock_service.get_sso_status = AsyncMock(
        return_value=_make_sso_status(has_oidc=True, oidc_provider="google")
    )

    with patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service):
        result = await get_sso_status(workspace_id=workspace_id, session=mock_session)

    assert isinstance(result, SsoStatusResponse)
    assert result.has_oidc is True
    assert result.oidc_provider == "google"


@pytest.mark.asyncio
async def test_sso_status_graceful_for_unknown_workspace() -> None:
    """GET /auth/sso/status returns all-false for unknown workspace_id.

    Scenario:
        Given workspace_id does not exist in the database
        When GET /auth/sso/status?workspace_id={id} is called
        Then the response is 200 with all-false (graceful degradation, no 404)

    This is intentional: the login page calls this before auth to decide
    whether to show an SSO button; it should degrade gracefully.
    """
    from pilot_space.api.v1.routers.auth_sso import get_sso_status
    from pilot_space.api.v1.schemas.sso import SsoStatusResponse

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()

    mock_service = MagicMock()
    # SsoService.get_sso_status returns all-false for unknown workspace
    mock_service.get_sso_status = AsyncMock(return_value=_make_sso_status())

    with patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service):
        result = await get_sso_status(workspace_id=workspace_id, session=mock_session)

    assert isinstance(result, SsoStatusResponse)
    assert result.has_saml is False
    assert result.has_oidc is False
    assert result.sso_required is False
    assert result.oidc_provider is None


# ---------------------------------------------------------------------------
# AUTH-04: SSO-only enforcement — check_sso_login_allowed endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sso_only_workspace_rejects_password_login() -> None:
    """check_sso_login_allowed returns 403 when workspace has sso_required=True.

    Scenario:
        Given workspace has SSO-only enforcement enabled (sso_required=True)
        When POST /auth/sso/check-login is called
        Then the response status is 403
        And the detail contains 'SSO login'
    """
    from pilot_space.api.v1.routers.auth_sso import check_sso_login_allowed
    from pilot_space.domain.exceptions import ForbiddenError

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()

    mock_service = MagicMock()
    mock_service.get_sso_status = AsyncMock(
        return_value=_make_sso_status(has_saml=True, sso_required=True)
    )

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        pytest.raises(ForbiddenError) as exc_info,
    ):
        await check_sso_login_allowed(workspace_id=workspace_id, session=mock_session)

    assert exc_info.value.http_status == 403


@pytest.mark.asyncio
async def test_sso_only_error_message_is_clear() -> None:
    """check_sso_login_allowed 403 body contains 'requires SSO login' message.

    Scenario:
        Given workspace.sso_required=True
        When check_sso_login_allowed is called
        Then the detail clearly states SSO is required
    """
    from pilot_space.api.v1.routers.auth_sso import check_sso_login_allowed
    from pilot_space.domain.exceptions import ForbiddenError

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()

    mock_service = MagicMock()
    mock_service.get_sso_status = AsyncMock(
        return_value=_make_sso_status(has_saml=True, sso_required=True)
    )

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        pytest.raises(ForbiddenError) as exc_info,
    ):
        await check_sso_login_allowed(workspace_id=workspace_id, session=mock_session)

    assert "requires SSO login" in exc_info.value.message


@pytest.mark.asyncio
async def test_non_sso_workspace_allows_password_login() -> None:
    """check_sso_login_allowed returns 200 when sso_required=False.

    Scenario:
        Given workspace has sso_required=False
        When check_sso_login_allowed is called
        Then no exception is raised (login allowed)
    """
    from pilot_space.api.v1.routers.auth_sso import check_sso_login_allowed

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()

    mock_service = MagicMock()
    mock_service.get_sso_status = AsyncMock(return_value=_make_sso_status(sso_required=False))

    with patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service):
        result = await check_sso_login_allowed(workspace_id=workspace_id, session=mock_session)

    assert result["password_login_allowed"] is True


# ---------------------------------------------------------------------------
# AUTH-01: SAML initiate redirect + tampered callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_saml_initiate_returns_redirect_url() -> None:
    """GET /auth/sso/saml/initiate returns {redirect_url} for a configured workspace.

    Scenario:
        Given workspace has SAML configured
        And SamlAuthProvider.get_login_url returns an IdP URL
        When initiate_saml_login is called
        Then the result contains redirect_url starting with https://
    """
    from unittest.mock import MagicMock

    from pilot_space.api.v1.routers.auth_sso import initiate_saml_login
    from pilot_space.api.v1.schemas.sso import SsoInitiateResponse

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_request = MagicMock()
    mock_request.base_url = "https://app.example.com"

    saml_config = {
        "entity_id": "https://idp.example.com/saml",
        "sso_url": "https://idp.example.com/saml/sso",
        "certificate": "MIID...",
        "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    }
    mock_service = MagicMock()
    mock_service.get_saml_config = AsyncMock(return_value=saml_config)

    expected_url = "https://okta.example.com/saml/sso?SAMLRequest=abc123"

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        patch("pilot_space.api.v1.routers.auth_sso._get_saml_provider") as mock_provider_factory,
    ):
        mock_provider = MagicMock()
        mock_provider.get_login_url.return_value = expected_url
        mock_provider_factory.return_value = mock_provider

        result = await initiate_saml_login(
            request=mock_request,
            workspace_id=workspace_id,
            session=mock_session,
            return_to="/dashboard",
        )

    assert isinstance(result, SsoInitiateResponse)
    assert result.redirect_url.startswith("https://")
    assert result.redirect_url == expected_url


@pytest.mark.asyncio
async def test_saml_callback_rejects_tampered_assertion() -> None:
    """POST /auth/sso/saml/callback returns 401 when assertion signature is invalid.

    Scenario:
        Given SamlAuthProvider.process_response raises SamlValidationError
        When saml_callback is called with tampered SAMLResponse
        Then the response status is 401
    """
    from pilot_space.api.v1.routers.auth_sso import saml_callback
    from pilot_space.infrastructure.auth.saml_auth import SamlValidationError

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_request = MagicMock()

    saml_config = {
        "entity_id": "https://idp.example.com/saml",
        "sso_url": "https://idp.example.com/saml/sso",
        "certificate": "MIID...",
    }
    mock_service = MagicMock()
    mock_service.get_saml_config = AsyncMock(return_value=saml_config)

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        patch("pilot_space.api.v1.routers.auth_sso._get_saml_provider") as mock_provider_factory,
    ):
        mock_provider = MagicMock()
        mock_provider.process_response.side_effect = SamlValidationError("Invalid signature")
        mock_provider_factory.return_value = mock_provider

        with pytest.raises(SamlValidationError) as exc_info:
            await saml_callback(
                request=mock_request,
                workspace_id=workspace_id,
                session=mock_session,
                SAMLResponse="tampered-base64-data",
                RelayState="",
            )

    assert exc_info.value.http_status == 401


# ---------------------------------------------------------------------------
# AUTH-03: claim-role endpoint applies mapped role
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_role_applies_mapped_role() -> None:
    """POST /auth/sso/claim-role applies admin role when claims match mapping.

    Scenario:
        Given user is authenticated
        And workspace has role claim mapping: groups=eng-leads → admin
        And JWT claims contain groups=eng-leads
        When claim_sso_role is called
        Then the response contains role='admin'
    """
    from pilot_space.api.v1.routers.auth_sso import claim_sso_role
    from pilot_space.api.v1.schemas.sso import SsoClaimRoleRequest, SsoClaimRoleResponse
    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
        WorkspaceRole,
    )

    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    # Create a mock member with ADMIN role (result of apply_sso_role)
    mock_member = MagicMock(spec=WorkspaceMember)
    mock_member.role = WorkspaceRole.ADMIN

    mock_service = MagicMock()
    mock_service.apply_sso_role = AsyncMock(return_value=mock_member)

    # Build mock current_user
    from dataclasses import dataclass

    @dataclass
    class MockTokenPayload:
        sub: str

        @property
        def user_id(self):  # type: ignore[override]
            return uuid.UUID(self.sub)

    mock_current_user = MockTokenPayload(sub=str(user_id))

    body = SsoClaimRoleRequest(
        workspace_id=workspace_id,
        jwt_claims={"groups": "eng-leads"},
    )

    with patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service):
        result = await claim_sso_role(
            body=body,
            session=mock_session,
            current_user=mock_current_user,  # type: ignore[arg-type]
        )

    mock_service.apply_sso_role.assert_called_once_with(
        user_id=mock_current_user.user_id,
        workspace_id=workspace_id,
        jwt_claims={"groups": "eng-leads"},
    )
    assert isinstance(result, SsoClaimRoleResponse)
    assert result.role == "admin"


# ---------------------------------------------------------------------------
# New tests — slug-based admin endpoints + SAML callback redirect (RED phase)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_configure_saml_accepts_workspace_slug() -> None:
    """POST /saml/config accepts workspace_slug string (not UUID), returns SamlConfigResponse.

    Scenario:
        Given workspace_slug="test-workspace" resolves to a valid UUID
        And configure_saml completes successfully
        When configure_saml endpoint is called with workspace_slug
        Then result is SamlConfigResponse (not 422)
    """
    from pilot_space.api.v1.routers.auth_sso import configure_saml
    from pilot_space.api.v1.schemas.sso import SamlConfigRequest, SamlConfigResponse

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_service = MagicMock()
    mock_service.configure_saml = AsyncMock(return_value=None)

    body = SamlConfigRequest(
        entity_id="https://idp.example.com/saml",
        sso_url="https://idp.example.com/saml/sso",  # type: ignore[arg-type]
        certificate="MIID...",
    )

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        patch(
            "pilot_space.api.v1.routers.auth_sso._resolve_workspace",
            new=AsyncMock(return_value=workspace_id),
        ),
        patch(
            "pilot_space.api.v1.routers.auth_sso.check_permission",
            new=AsyncMock(return_value=True),
        ),
    ):
        result = await configure_saml(
            workspace_slug="test-workspace",
            body=body,
            session=mock_session,
            current_user=MagicMock(user_id=uuid.uuid4()),  # type: ignore[arg-type]
        )

    assert isinstance(result, SamlConfigResponse)


@pytest.mark.asyncio
async def test_configure_oidc_accepts_workspace_slug() -> None:
    """POST /oidc/config accepts workspace_slug string (not UUID), returns OidcConfigResponse.

    Scenario:
        Given workspace_slug="test-workspace" resolves to a valid UUID
        And configure_oidc completes successfully
        When configure_oidc endpoint is called with workspace_slug
        Then result is OidcConfigResponse (not 422)
    """
    from pilot_space.api.v1.routers.auth_sso import configure_oidc
    from pilot_space.api.v1.schemas.sso import OidcConfigRequest, OidcConfigResponse

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_service = MagicMock()
    mock_service.configure_oidc = AsyncMock(return_value=None)

    body = OidcConfigRequest(
        provider="google",
        client_id="client-id-123",
        client_secret="test-value-not-real",  # pragma: allowlist secret
        issuer_url=None,
    )

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        patch(
            "pilot_space.api.v1.routers.auth_sso._resolve_workspace",
            new=AsyncMock(return_value=workspace_id),
        ),
        patch(
            "pilot_space.api.v1.routers.auth_sso.check_permission",
            new=AsyncMock(return_value=True),
        ),
    ):
        result = await configure_oidc(
            workspace_slug="test-workspace",
            body=body,
            session=mock_session,
            current_user=MagicMock(user_id=uuid.uuid4()),  # type: ignore[arg-type]
        )

    assert isinstance(result, OidcConfigResponse)


@pytest.mark.asyncio
async def test_set_sso_enforcement_accepts_workspace_slug() -> None:
    """PATCH /enforcement accepts workspace_slug string (not UUID), returns None (204).

    Scenario:
        Given workspace_slug="test-workspace" resolves to a valid UUID
        And set_sso_required completes successfully
        When set_sso_enforcement endpoint is called with workspace_slug
        Then result is None (204 No Content, not 422)
    """
    from pilot_space.api.v1.routers.auth_sso import set_sso_enforcement
    from pilot_space.api.v1.schemas.sso import SsoEnforcementRequest

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_service = MagicMock()
    mock_service.set_sso_required = AsyncMock(return_value=None)

    body = SsoEnforcementRequest(sso_required=True)

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        patch(
            "pilot_space.api.v1.routers.auth_sso._resolve_workspace",
            new=AsyncMock(return_value=workspace_id),
        ),
        patch(
            "pilot_space.api.v1.routers.auth_sso.check_permission",
            new=AsyncMock(return_value=True),
        ),
    ):
        result = await set_sso_enforcement(
            workspace_slug="test-workspace",
            body=body,
            session=mock_session,
            current_user=MagicMock(user_id=uuid.uuid4()),  # type: ignore[arg-type]
        )

    assert result is None


@pytest.mark.asyncio
async def test_saml_callback_redirects_with_token_hash() -> None:
    """POST /saml/callback returns a RedirectResponse with token_hash in URL.

    Scenario:
        Given a valid SAML assertion from the IdP
        And provision_saml_user returns {token_hash: "abc123"}
        When saml_callback processes the assertion
        Then result is a RedirectResponse
        And location header contains "token_hash=abc123"
    """
    from fastapi.responses import RedirectResponse

    from pilot_space.api.v1.routers.auth_sso import saml_callback

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_request = MagicMock()

    saml_attributes = {
        "email": ["user@example.com"],
        "displayName": ["Test User"],
    }
    saml_result = {
        "name_id": "user@example.com",
        "attributes": saml_attributes,
    }

    mock_service = MagicMock()
    mock_service.get_saml_config = AsyncMock(
        return_value={
            "entity_id": "https://idp.example.com/saml",
            "sso_url": "https://idp.example.com/saml/sso",
            "certificate": "MIID...",
        }
    )
    mock_service.provision_saml_user = AsyncMock(
        return_value={
            "user_id": str(uuid.uuid4()),
            "email": "user@example.com",
            "is_new": False,
            "token_hash": "abc123",
        }
    )

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        patch("pilot_space.api.v1.routers.auth_sso._get_saml_provider") as mock_provider_factory,
        patch("pilot_space.api.v1.routers.auth_sso.get_settings") as mock_settings,
    ):
        mock_provider = MagicMock()
        mock_provider.process_response.return_value = saml_result
        mock_provider_factory.return_value = mock_provider

        mock_settings_obj = MagicMock()
        mock_settings_obj.frontend_url = "https://app.example.com"
        mock_settings.return_value = mock_settings_obj

        result = await saml_callback(
            request=mock_request,
            workspace_id=workspace_id,
            session=mock_session,
            SAMLResponse="valid-saml-response-base64",
            RelayState="",
        )

    assert isinstance(result, RedirectResponse)
    location = result.headers.get("location", "")
    assert "token_hash=abc123" in location


@pytest.mark.asyncio
async def test_get_saml_config_accepts_workspace_slug() -> None:
    """GET /saml/config accepts workspace_slug string, returns SamlConfigResponse.

    Scenario:
        Given workspace_slug="test-workspace" resolves to a valid UUID
        And SAML config is stored
        When get_saml_config is called with workspace_slug
        Then result is SamlConfigResponse (not 422)
    """
    from pilot_space.api.v1.routers.auth_sso import get_saml_config
    from pilot_space.api.v1.schemas.sso import SamlConfigResponse

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()

    mock_service = MagicMock()
    mock_service.get_saml_config = AsyncMock(
        return_value={
            "entity_id": "https://idp.example.com/saml",
            "sso_url": "https://idp.example.com/saml/sso",
        }
    )

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        patch(
            "pilot_space.api.v1.routers.auth_sso._resolve_workspace",
            new=AsyncMock(return_value=workspace_id),
        ),
        patch(
            "pilot_space.api.v1.routers.auth_sso.check_permission",
            new=AsyncMock(return_value=True),
        ),
        patch("pilot_space.api.v1.routers.auth_sso.get_settings") as mock_settings,
    ):
        mock_settings_obj = MagicMock()
        mock_settings_obj.backend_url = "https://api.example.com"
        mock_settings.return_value = mock_settings_obj

        result = await get_saml_config(
            workspace_slug="test-workspace",
            session=mock_session,
            current_user=MagicMock(user_id=uuid.uuid4()),  # type: ignore[arg-type]
        )

    assert isinstance(result, SamlConfigResponse)


@pytest.mark.asyncio
async def test_get_role_claim_mapping_accepts_workspace_slug() -> None:
    """GET /role-mapping accepts workspace_slug string, returns RoleClaimMappingConfig.

    Scenario:
        Given workspace_slug="test-workspace" resolves to a valid UUID
        And role claim mapping is stored
        When get_role_claim_mapping is called with workspace_slug
        Then result is RoleClaimMappingConfig (not 422)
    """
    from pilot_space.api.v1.routers.auth_sso import get_role_claim_mapping
    from pilot_space.api.v1.schemas.sso import RoleClaimMappingConfig

    workspace_id = uuid.uuid4()
    mock_session = AsyncMock()

    mock_service = MagicMock()
    mock_service.get_role_claim_mapping = AsyncMock(
        return_value={
            "claim_key": "groups",
            "mappings": [{"claim_value": "eng-leads", "role": "admin"}],
        }
    )

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        patch(
            "pilot_space.api.v1.routers.auth_sso._resolve_workspace",
            new=AsyncMock(return_value=workspace_id),
        ),
        patch(
            "pilot_space.api.v1.routers.auth_sso.check_permission",
            new=AsyncMock(return_value=True),
        ),
    ):
        result = await get_role_claim_mapping(
            workspace_slug="test-workspace",
            session=mock_session,
            current_user=MagicMock(user_id=uuid.uuid4()),  # type: ignore[arg-type]
        )

    assert isinstance(result, RoleClaimMappingConfig)


# ---------------------------------------------------------------------------
# AUDIT-01: SAML callback writes user.login audit entry
# ---------------------------------------------------------------------------

_SAML_CALLBACK_PATCHES = {
    "saml_config": {
        "entity_id": "https://idp.example.com/saml",
        "sso_url": "https://idp.example.com/saml/sso",
        "certificate": "MIID...",
    },
    "saml_result": {
        "name_id": "user@example.com",
        "attributes": {"email": ["user@example.com"]},
    },
    "user_info": {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "is_new": False,
        "token_hash": "tok",
    },
    "frontend_url": "https://app.example.com",
}


def _build_saml_callback_mocks(audit_side_effect=None):
    """Build standard mock set for AUDIT-01 saml_callback tests."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.client = MagicMock()
    mock_request.client.host = "127.0.0.1"

    user_info = _SAML_CALLBACK_PATCHES["user_info"]
    mock_service = MagicMock()
    mock_service.get_saml_config = AsyncMock(return_value=_SAML_CALLBACK_PATCHES["saml_config"])
    mock_service.provision_saml_user = AsyncMock(return_value=user_info)

    mock_provider = MagicMock()
    mock_provider.process_response.return_value = _SAML_CALLBACK_PATCHES["saml_result"]

    mock_settings_obj = MagicMock()
    mock_settings_obj.frontend_url = _SAML_CALLBACK_PATCHES["frontend_url"]

    mock_audit = AsyncMock(side_effect=audit_side_effect)

    return mock_session, mock_request, mock_service, mock_provider, mock_settings_obj, mock_audit


@pytest.mark.asyncio
async def test_saml_callback_writes_login_audit_entry() -> None:
    """saml_callback calls write_audit_nonfatal with correct kwargs on successful login.

    Scenario:
        Given a valid SAML assertion and successful user provisioning
        When saml_callback processes the assertion
        Then write_audit_nonfatal is called with:
            - action="user.login"
            - resource_type="user"
            - workspace_id matches the route param
            - actor_id=UUID(user_info["user_id"])
            - resource_id=UUID(user_info["user_id"])
            - payload={"method": "saml", "is_new": False}
    """
    from fastapi.responses import RedirectResponse

    from pilot_space.api.v1.routers.auth_sso import saml_callback

    workspace_id = uuid.uuid4()
    (
        mock_session,
        mock_request,
        mock_service,
        mock_provider,
        mock_settings_obj,
        mock_audit,
    ) = _build_saml_callback_mocks()

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        patch(
            "pilot_space.api.v1.routers.auth_sso._get_saml_provider",
            return_value=mock_provider,
        ),
        patch(
            "pilot_space.api.v1.routers.auth_sso.get_settings",
            return_value=mock_settings_obj,
        ),
        patch(
            "pilot_space.api.v1.routers.auth_sso.write_audit_nonfatal",
            mock_audit,
        ),
    ):
        result = await saml_callback(
            request=mock_request,
            workspace_id=workspace_id,
            session=mock_session,
            SAMLResponse="valid-saml-response",
            RelayState="",
        )

    assert isinstance(result, RedirectResponse)
    mock_audit.assert_called_once()
    _kw = mock_audit.call_args.kwargs
    assert _kw["action"] == "user.login"
    assert _kw["resource_type"] == "user"
    assert _kw["workspace_id"] == workspace_id
    expected_uid = uuid.UUID(_SAML_CALLBACK_PATCHES["user_info"]["user_id"])
    assert _kw["actor_id"] == expected_uid
    assert _kw["resource_id"] == expected_uid
    assert _kw["payload"] == {"method": "saml", "is_new": False}


@pytest.mark.asyncio
async def test_saml_callback_audit_is_after_commit() -> None:
    """write_audit_nonfatal is called only AFTER session.commit() on successful login.

    Scenario:
        Given a valid SAML assertion
        When saml_callback processes the assertion
        Then session.commit() call count is >= 1 before write_audit_nonfatal is awaited
    """
    from pilot_space.api.v1.routers.auth_sso import saml_callback

    workspace_id = uuid.uuid4()
    (
        mock_session,
        mock_request,
        mock_service,
        mock_provider,
        mock_settings_obj,
        _,
    ) = _build_saml_callback_mocks()

    call_order: list[str] = []

    async def _track_commit(*_args: object, **_kwargs: object) -> None:
        call_order.append("commit")

    async def _track_audit(*_args: object, **_kwargs: object) -> None:
        call_order.append("audit")

    mock_session.commit = AsyncMock(side_effect=_track_commit)

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        patch(
            "pilot_space.api.v1.routers.auth_sso._get_saml_provider",
            return_value=mock_provider,
        ),
        patch(
            "pilot_space.api.v1.routers.auth_sso.get_settings",
            return_value=mock_settings_obj,
        ),
        patch(
            "pilot_space.api.v1.routers.auth_sso.write_audit_nonfatal",
            side_effect=_track_audit,
        ),
    ):
        await saml_callback(
            request=mock_request,
            workspace_id=workspace_id,
            session=mock_session,
            SAMLResponse="valid-saml-response",
            RelayState="",
        )

    assert "commit" in call_order
    assert "audit" in call_order
    commit_idx = call_order.index("commit")
    audit_idx = call_order.index("audit")
    assert commit_idx < audit_idx, f"commit must precede audit; got order: {call_order}"


@pytest.mark.asyncio
async def test_saml_callback_succeeds_when_audit_raises() -> None:
    """saml_callback returns RedirectResponse even when write_audit_nonfatal raises.

    Scenario:
        Given a valid SAML assertion and successful user provisioning
        And write_audit_nonfatal raises an unexpected Exception
        When saml_callback processes the assertion
        Then the result is still a RedirectResponse (non-fatal guarantee)
        And no exception propagates to the caller
    """
    from fastapi.responses import RedirectResponse

    from pilot_space.api.v1.routers.auth_sso import saml_callback

    workspace_id = uuid.uuid4()
    (
        mock_session,
        mock_request,
        mock_service,
        mock_provider,
        mock_settings_obj,
        mock_audit,
    ) = _build_saml_callback_mocks(audit_side_effect=Exception("audit DB failure"))

    with (
        patch("pilot_space.api.v1.routers.auth_sso._get_sso_service", return_value=mock_service),
        patch(
            "pilot_space.api.v1.routers.auth_sso._get_saml_provider",
            return_value=mock_provider,
        ),
        patch(
            "pilot_space.api.v1.routers.auth_sso.get_settings",
            return_value=mock_settings_obj,
        ),
        patch(
            "pilot_space.api.v1.routers.auth_sso.write_audit_nonfatal",
            mock_audit,
        ),
    ):
        result = await saml_callback(
            request=mock_request,
            workspace_id=workspace_id,
            session=mock_session,
            SAMLResponse="valid-saml-response",
            RelayState="",
        )

    assert isinstance(result, RedirectResponse)
