"""Unit tests for SsoService — AUTH-01 through AUTH-04.

All tests use mocked WorkspaceRepository and Supabase admin client.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.sso_service import SsoService
from pilot_space.infrastructure.database.models.workspace import Workspace


def _make_workspace(settings: dict[str, Any] | None = None) -> MagicMock:
    ws = MagicMock(spec=Workspace)
    ws.id = uuid4()
    ws.settings = settings
    ws.is_deleted = False
    return ws


def _make_service(workspace: MagicMock | None = None) -> tuple[SsoService, MagicMock]:
    workspace_repo = MagicMock()
    workspace_repo.session = AsyncMock()
    workspace_repo.session.flush = AsyncMock()
    if workspace is not None:
        workspace_repo.get_by_id = AsyncMock(return_value=workspace)
    else:
        workspace_repo.get_by_id = AsyncMock(return_value=None)
    admin_client = MagicMock()
    service = SsoService(workspace_repo=workspace_repo, supabase_admin_client=admin_client)
    return service, workspace_repo


@pytest.mark.asyncio
async def test_saml_config_stored_and_retrieved() -> None:
    """SAML config is persisted to workspace.settings and can be retrieved."""
    ws = _make_workspace()
    service, _ = _make_service(ws)
    config = {
        "entity_id": "https://idp.example.com/saml",
        "sso_url": "https://idp.example.com/saml/sso",
        "certificate": "MIID...",
    }
    await service.configure_saml(UUID(str(ws.id)), config)
    assert ws.settings is not None
    assert "saml_config" in ws.settings
    saml = ws.settings["saml_config"]
    assert saml["entity_id"] == config["entity_id"]
    assert saml["certificate"] == config["certificate"]
    assert "name_id_format" in saml


@pytest.mark.asyncio
async def test_saml_config_merges_not_replaces() -> None:
    """configure_saml merges into existing settings without removing other keys."""
    ws = _make_workspace(settings={"some_other_key": "preserved_value"})
    service, _ = _make_service(ws)
    config = {"entity_id": "e", "sso_url": "https://u", "certificate": "c"}
    await service.configure_saml(UUID(str(ws.id)), config)
    assert ws.settings is not None
    assert ws.settings.get("some_other_key") == "preserved_value"
    assert "saml_config" in ws.settings


@pytest.mark.asyncio
async def test_saml_config_missing_required_fields_raises() -> None:
    """configure_saml raises ValueError when required fields are absent."""
    ws = _make_workspace()
    service, _ = _make_service(ws)
    with pytest.raises(ValueError, match="missing required fields"):
        await service.configure_saml(UUID(str(ws.id)), {"entity_id": "only"})


@pytest.mark.asyncio
async def test_get_saml_config_returns_none_when_no_settings() -> None:
    """get_saml_config returns None when workspace has no settings."""
    ws = _make_workspace(settings=None)
    service, _ = _make_service(ws)
    assert await service.get_saml_config(UUID(str(ws.id))) is None


@pytest.mark.asyncio
async def test_get_saml_config_returns_stored_config() -> None:
    """get_saml_config returns the stored SAML config dict."""
    saml_data = {
        "entity_id": "https://idp.example.com",
        "sso_url": "https://idp.example.com/sso",
        "certificate": "cert",
        "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    }
    ws = _make_workspace(settings={"saml_config": saml_data})
    service, _ = _make_service(ws)
    assert await service.get_saml_config(UUID(str(ws.id))) == saml_data


@pytest.mark.asyncio
async def test_oidc_config_stored_and_retrieved() -> None:
    """OIDC config is persisted to workspace.settings and can be retrieved."""
    ws = _make_workspace()
    service, _ = _make_service(ws)
    config = {"provider": "google", "client_id": "cid", "client_secret": "sec"}
    await service.configure_oidc(UUID(str(ws.id)), config)
    assert ws.settings is not None
    oidc = ws.settings["oidc_config"]
    assert oidc["provider"] == "google"
    assert oidc["client_id"] == "cid"


@pytest.mark.asyncio
async def test_oidc_config_merges_not_replaces() -> None:
    """configure_oidc merges into existing settings without removing other keys."""
    ws = _make_workspace(settings={"saml_config": {"entity_id": "existing"}})
    service, _ = _make_service(ws)
    await service.configure_oidc(
        UUID(str(ws.id)),
        {"provider": "azure", "client_id": "c1", "client_secret": "s1"},
    )
    assert ws.settings is not None
    assert ws.settings.get("saml_config", {}).get("entity_id") == "existing"
    assert "oidc_config" in ws.settings


@pytest.mark.asyncio
async def test_sso_required_flag_set() -> None:
    """set_sso_required(True) stores sso_required=True in workspace.settings."""
    ws = _make_workspace()
    service, _ = _make_service(ws)
    await service.set_sso_required(UUID(str(ws.id)), required=True)
    assert ws.settings is not None
    assert ws.settings["sso_required"] is True


@pytest.mark.asyncio
async def test_get_sso_status_no_config() -> None:
    """Workspace with no settings returns all False/None status."""
    ws = _make_workspace(settings=None)
    service, _ = _make_service(ws)
    result = await service.get_sso_status(UUID(str(ws.id)))
    assert result == {
        "has_saml": False,
        "has_oidc": False,
        "sso_required": False,
        "oidc_provider": None,
    }


@pytest.mark.asyncio
async def test_get_sso_status_with_saml() -> None:
    """Workspace with saml_config returns has_saml=True."""
    ws = _make_workspace(
        settings={"saml_config": {"entity_id": "https://idp", "sso_url": "u", "certificate": "c"}}
    )
    service, _ = _make_service(ws)
    result = await service.get_sso_status(UUID(str(ws.id)))
    assert result["has_saml"] is True
    assert result["has_oidc"] is False
    assert result["oidc_provider"] is None


@pytest.mark.asyncio
async def test_get_sso_status_unknown_workspace() -> None:
    """Non-existent workspace_id returns all False/None (graceful degradation)."""
    service, _ = _make_service(workspace=None)
    result = await service.get_sso_status(uuid4())
    assert result == {
        "has_saml": False,
        "has_oidc": False,
        "sso_required": False,
        "oidc_provider": None,
    }


# ---------------------------------------------------------------------------
# AUTH-03: Role claim mapping (map_claims_to_role, configure, apply)
# ---------------------------------------------------------------------------

_SAMPLE_MAPPING_CONFIG = {
    "claim_key": "groups",
    "mappings": [
        {"claim_value": "eng-leads", "role": "admin"},
        {"claim_value": "developers", "role": "member"},
    ],
}


def test_role_claim_mapping_applies_correct_role() -> None:
    """map_claims_to_role returns 'admin' when claim matches eng-leads mapping."""
    from pilot_space.application.services.sso_service import SsoService

    result = SsoService.map_claims_to_role("eng-leads", _SAMPLE_MAPPING_CONFIG)
    assert result == "admin"


def test_unmapped_claim_defaults_to_member() -> None:
    """map_claims_to_role returns 'member' for unmapped claim values."""
    from pilot_space.application.services.sso_service import SsoService

    result = SsoService.map_claims_to_role("unknown-group", _SAMPLE_MAPPING_CONFIG)
    assert result == "member"


def test_owner_mapping_capped_at_admin() -> None:
    """map_claims_to_role caps 'owner' mapping to 'admin' — OWNER cannot be assigned via SSO."""
    from pilot_space.application.services.sso_service import SsoService

    config_with_owner = {
        "claim_key": "groups",
        "mappings": [{"claim_value": "super-admins", "role": "owner"}],
    }
    result = SsoService.map_claims_to_role("super-admins", config_with_owner)
    assert result == "admin"


def test_list_claim_value_matches_any() -> None:
    """map_claims_to_role handles list claim values — matches first item in list."""
    from pilot_space.application.services.sso_service import SsoService

    result = SsoService.map_claims_to_role(["devs", "eng-leads"], _SAMPLE_MAPPING_CONFIG)
    assert result == "admin"


def test_case_insensitive_claim_matching() -> None:
    """map_claims_to_role matches case-insensitively — ENG-LEADS matches eng-leads config."""
    from pilot_space.application.services.sso_service import SsoService

    result = SsoService.map_claims_to_role("ENG-LEADS", _SAMPLE_MAPPING_CONFIG)
    assert result == "admin"


def test_empty_mapping_config_defaults_to_member() -> None:
    """map_claims_to_role returns 'member' when mappings list is empty."""
    from pilot_space.application.services.sso_service import SsoService

    result = SsoService.map_claims_to_role("any-group", {"claim_key": "groups", "mappings": []})
    assert result == "member"


@pytest.mark.asyncio
async def test_sso_required_flag_stored() -> None:
    """set_sso_required(True) stores sso_required=True in workspace.settings."""
    ws = _make_workspace()
    service, _ = _make_service(ws)
    await service.set_sso_required(UUID(str(ws.id)), required=True)
    assert ws.settings is not None
    assert ws.settings["sso_required"] is True


@pytest.mark.asyncio
async def test_oidc_config_stored_merges_not_replaces() -> None:
    """configure_oidc preserves other settings keys when storing oidc_config."""
    ws = _make_workspace(settings={"existing_key": "preserved", "saml_config": {"entity_id": "x"}})
    service, _ = _make_service(ws)
    config = {"provider": "okta", "client_id": "c", "client_secret": "s"}
    await service.configure_oidc(UUID(str(ws.id)), config)
    assert ws.settings is not None
    assert ws.settings.get("existing_key") == "preserved"
    assert ws.settings.get("saml_config", {}).get("entity_id") == "x"
    assert "oidc_config" in ws.settings


@pytest.mark.asyncio
async def test_configure_role_claim_mapping_stores_config() -> None:
    """configure_role_claim_mapping stores mapping config in workspace.settings."""
    ws = _make_workspace()
    service, _ = _make_service(ws)
    await service.configure_role_claim_mapping(
        UUID(str(ws.id)),
        claim_key="groups",
        mappings=[{"claim_value": "eng-leads", "role": "admin"}],
    )
    assert ws.settings is not None
    mapping = ws.settings["role_claim_mapping"]
    assert mapping["claim_key"] == "groups"
    assert len(mapping["mappings"]) == 1
    assert mapping["mappings"][0]["claim_value"] == "eng-leads"


@pytest.mark.asyncio
async def test_get_role_claim_mapping_returns_none_when_not_configured() -> None:
    """get_role_claim_mapping returns None when no mapping config exists."""
    ws = _make_workspace(settings=None)
    service, _ = _make_service(ws)
    result = await service.get_role_claim_mapping(UUID(str(ws.id)))
    assert result is None


@pytest.mark.asyncio
async def test_apply_sso_role_updates_member_role() -> None:
    """apply_sso_role updates WorkspaceMember.role based on JWT claims."""
    from unittest.mock import patch

    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
        WorkspaceRole,
    )

    ws = _make_workspace(
        settings={
            "role_claim_mapping": {
                "claim_key": "groups",
                "mappings": [{"claim_value": "eng-leads", "role": "admin"}],
            }
        }
    )
    workspace_id = UUID(str(ws.id))
    user_id = uuid4()

    mock_member = MagicMock(spec=WorkspaceMember)
    mock_member.role = WorkspaceRole.MEMBER

    service, workspace_repo = _make_service(ws)

    with patch.object(service, "_get_member_for_user", new=AsyncMock(return_value=mock_member)):
        result = await service.apply_sso_role(
            user_id=user_id,
            workspace_id=workspace_id,
            jwt_claims={"groups": "eng-leads"},
        )

    assert mock_member.role == WorkspaceRole.ADMIN
    assert result is mock_member


# ---------------------------------------------------------------------------
# New tests — provision_saml_user calls generate_link (RED phase)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provision_saml_user_calls_generate_link() -> None:
    """provision_saml_user calls admin.generate_link and returns token_hash for new user.

    Scenario:
        Given a new user (list_users returns empty)
        And admin.create_user creates the user
        And admin.generate_link returns a magic link with hashed_token="test-hash"
        When provision_saml_user is called
        Then the returned dict contains token_hash="test-hash"
        And admin.generate_link was called with type="magiclink"
    """
    from unittest.mock import patch

    ws = _make_workspace()
    workspace_id = UUID(str(ws.id))
    new_user_id = uuid4()

    service, workspace_repo = _make_service(ws)
    admin = service._admin_client.auth.admin

    # New user — list_users returns empty
    admin.list_users = AsyncMock(return_value=[])

    # create_user returns a user
    mock_created_user = MagicMock()
    mock_created_user.user.id = new_user_id
    admin.create_user = AsyncMock(return_value=mock_created_user)

    # generate_link returns magic link result
    mock_link_result = MagicMock()
    mock_link_result.properties.hashed_token = "test-hash"
    admin.generate_link = AsyncMock(return_value=mock_link_result)

    with patch("pilot_space.application.services.sso_service.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.frontend_url = "https://app.example.com"
        mock_get_settings.return_value = mock_settings

        # Patch _ensure_workspace_member to avoid DB access
        with patch.object(service, "_ensure_workspace_member", new=AsyncMock(return_value=None)):
            result = await service.provision_saml_user(
                email="newuser@example.com",
                display_name="New User",
                workspace_id=workspace_id,
            )

    assert result["token_hash"] == "test-hash"
    admin.generate_link.assert_called_once()
    call_kwargs = admin.generate_link.call_args[0][0]
    assert call_kwargs["type"] == "magiclink"
    assert call_kwargs["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_provision_saml_user_returns_token_hash_for_existing_user() -> None:
    """provision_saml_user calls generate_link and returns token_hash for existing user.

    Scenario:
        Given an existing user (list_users returns matching user)
        And admin.update_user_by_id succeeds
        And admin.generate_link returns a magic link with hashed_token="existing-hash"
        When provision_saml_user is called
        Then the returned dict contains token_hash="existing-hash"
        And is_new is False
    """
    from unittest.mock import patch

    ws = _make_workspace()
    workspace_id = UUID(str(ws.id))
    existing_user_id = uuid4()

    service, workspace_repo = _make_service(ws)
    admin = service._admin_client.auth.admin

    # Existing user — list_users returns matching user
    mock_existing_user = MagicMock()
    mock_existing_user.email = "existing@example.com"
    mock_existing_user.id = existing_user_id
    admin.list_users = AsyncMock(return_value=[mock_existing_user])
    admin.update_user_by_id = AsyncMock(return_value=None)

    # generate_link returns magic link result
    mock_link_result = MagicMock()
    mock_link_result.properties.hashed_token = "existing-hash"
    admin.generate_link = AsyncMock(return_value=mock_link_result)

    with patch("pilot_space.application.services.sso_service.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.frontend_url = "https://app.example.com"
        mock_get_settings.return_value = mock_settings

        with patch.object(service, "_ensure_workspace_member", new=AsyncMock(return_value=None)):
            result = await service.provision_saml_user(
                email="existing@example.com",
                display_name="Existing User",
                workspace_id=workspace_id,
            )

    assert result["token_hash"] == "existing-hash"
    assert result["is_new"] is False
    admin.generate_link.assert_called_once()
