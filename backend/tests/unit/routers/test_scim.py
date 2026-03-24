"""Tests for SCIM 2.0 provisioning router and ScimService — AUTH-07.

Tests cover:
  - ScimService.provision_user: creates/reactivates workspace member
  - ScimService.deprovision_user: sets is_active=False, preserves data
  - ScimService.patch_user: applies RFC 7644 patch ops
  - ScimService.list_users: paginated workspace member list
  - ScimService.generate_scim_token: generates and stores SHA-256 hash
  - SCIM router bearer token auth enforcement
  - SCIM ListResponse endpoint
  - ServiceProviderConfig endpoint (no auth required)
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _make_user(
    *,
    email: str = "user@example.com",
    full_name: str | None = "Test User",
) -> MagicMock:
    u = MagicMock()
    u.id = uuid4()
    u.email = email
    u.full_name = full_name
    u.is_deleted = False
    return u


def _make_member(
    *,
    user_id=None,
    workspace_id=None,
    is_active: bool = True,
    email: str = "user@example.com",
    full_name: str | None = "Test User",
) -> MagicMock:
    m = MagicMock()
    m.id = uuid4()
    m.user_id = user_id or uuid4()
    m.workspace_id = workspace_id or uuid4()
    m.is_active = is_active
    m.is_deleted = False
    m.role = MagicMock()
    m.role.value = "MEMBER"
    m.user = _make_user(email=email, full_name=full_name)
    m.created_at = datetime.now(tz=UTC)
    m.updated_at = datetime.now(tz=UTC)
    return m


def _make_workspace(
    *,
    slug: str = "test-workspace",
    scim_token_hash: str | None = None,
) -> MagicMock:
    w = MagicMock()
    w.id = uuid4()
    w.slug = slug
    w.settings = {}
    if scim_token_hash:
        w.settings = {"scim_token_hash": scim_token_hash}
    w.is_deleted = False
    return w


class TestScimServiceProvisionUser:
    """Tests for ScimService.provision_user."""

    @pytest.mark.asyncio
    async def test_provision_new_user_creates_member(self) -> None:
        """provision_user creates Supabase user + workspace_member when email is new."""
        from pilot_space.application.services.scim_service import ScimService

        workspace_id = uuid4()
        new_user = _make_user(email="new@example.com")
        new_member = _make_member(workspace_id=workspace_id, email="new@example.com")

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = MagicMock()

        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=execute_result)

        service = ScimService(
            workspace_repo=MagicMock(),
            user_repo=MagicMock(),
            supabase_admin_client=MagicMock(),
        )

        with (
            patch.object(service, "_get_or_create_user", AsyncMock(return_value=new_user)),
            patch.object(service, "_get_or_create_member", AsyncMock(return_value=new_member)),
        ):
            result = await service.provision_user(
                workspace_id=workspace_id,
                email="new@example.com",
                display_name="New User",
                active=True,
                db=mock_session,
            )

        assert result.is_active is True
        assert result.workspace_id == workspace_id

    @pytest.mark.asyncio
    async def test_provision_existing_deprovisioned_user_reactivates(self) -> None:
        """provision_user re-enables is_active when user was previously deprovisioned."""
        from pilot_space.application.services.scim_service import ScimService

        workspace_id = uuid4()
        existing_user = _make_user(email="deprovisioned@example.com")
        existing_member = _make_member(
            workspace_id=workspace_id,
            email="deprovisioned@example.com",
            is_active=False,
        )

        service = ScimService(
            workspace_repo=MagicMock(),
            user_repo=MagicMock(),
            supabase_admin_client=MagicMock(),
        )

        mock_session = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        with (
            patch.object(service, "_get_or_create_user", AsyncMock(return_value=existing_user)),
            patch.object(service, "_get_or_create_member", AsyncMock(return_value=existing_member)),
        ):
            result = await service.provision_user(
                workspace_id=workspace_id,
                email="deprovisioned@example.com",
                display_name="Old User",
                active=True,
                db=mock_session,
            )

        assert result.is_active is True


class TestScimServiceDeprovisionUser:
    """Tests for ScimService.deprovision_user."""

    @pytest.mark.asyncio
    async def test_deprovision_sets_is_active_false(self) -> None:
        """deprovision_user sets is_active=False without deleting any data."""
        from pilot_space.application.services.scim_service import ScimService

        workspace_id = uuid4()
        user_id = uuid4()
        member = _make_member(user_id=user_id, workspace_id=workspace_id, is_active=True)

        mock_session = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=member)
        mock_session.execute = AsyncMock(return_value=execute_result)

        service = ScimService(
            workspace_repo=MagicMock(),
            user_repo=MagicMock(),
            supabase_admin_client=MagicMock(),
        )

        await service.deprovision_user(
            user_id=user_id,
            workspace_id=workspace_id,
            db=mock_session,
        )

        assert member.is_active is False

    @pytest.mark.asyncio
    async def test_deprovision_not_found_raises(self) -> None:
        """deprovision_user raises ScimUserNotFoundError if member not in workspace."""
        from pilot_space.application.services.scim_service import ScimService, ScimUserNotFoundError

        mock_session = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=execute_result)

        service = ScimService(
            workspace_repo=MagicMock(),
            user_repo=MagicMock(),
            supabase_admin_client=MagicMock(),
        )

        with pytest.raises(ScimUserNotFoundError, match="not found"):
            await service.deprovision_user(
                user_id=uuid4(),
                workspace_id=uuid4(),
                db=mock_session,
            )


class TestScimServicePatchUser:
    """Tests for ScimService.patch_user."""

    @pytest.mark.asyncio
    async def test_patch_active_false_deactivates_member(self) -> None:
        """patch_user with active=false calls deprovision_user."""
        from pilot_space.application.services.scim_service import ScimService

        workspace_id = uuid4()
        user_id = uuid4()
        member = _make_member(user_id=user_id, workspace_id=workspace_id, is_active=True)

        mock_session = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=member)
        mock_session.execute = AsyncMock(return_value=execute_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = ScimService(
            workspace_repo=MagicMock(),
            user_repo=MagicMock(),
            supabase_admin_client=MagicMock(),
        )

        patch_ops = [{"op": "replace", "path": "active", "value": False}]

        with (
            patch.object(
                service,
                "deprovision_user",
                AsyncMock(side_effect=lambda *_a, **_kw: setattr(member, "is_active", False)),
            ) as mock_deprovision,
            patch.object(service, "get_user", AsyncMock(return_value=member)),
        ):
            await service.patch_user(
                user_id=user_id,
                workspace_id=workspace_id,
                patch_ops=patch_ops,
                db=mock_session,
            )
        mock_deprovision.assert_called_once()

    @pytest.mark.asyncio
    async def test_patch_display_name_updates_user(self) -> None:
        """patch_user with displayName replace updates user.full_name."""
        from pilot_space.application.services.scim_service import ScimService

        workspace_id = uuid4()
        user_id = uuid4()
        member = _make_member(user_id=user_id, workspace_id=workspace_id, full_name="Old Name")

        mock_session = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=member)
        mock_session.execute = AsyncMock(return_value=execute_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = ScimService(
            workspace_repo=MagicMock(),
            user_repo=MagicMock(),
            supabase_admin_client=MagicMock(),
        )

        patch_ops = [{"op": "replace", "path": "displayName", "value": "New Name"}]

        with patch.object(service, "get_user", AsyncMock(return_value=member)):
            await service.patch_user(
                user_id=user_id,
                workspace_id=workspace_id,
                patch_ops=patch_ops,
                db=mock_session,
            )

        assert member.user.full_name == "New Name"


class TestScimServiceGenerateToken:
    """Tests for ScimService.generate_scim_token."""

    @pytest.mark.asyncio
    async def test_generate_token_stores_hash_in_workspace(self) -> None:
        """generate_scim_token stores SHA-256 hash in workspace.settings."""
        from pilot_space.application.services.scim_service import ScimService

        workspace = _make_workspace()
        mock_session = MagicMock()
        mock_session.flush = AsyncMock()

        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=workspace)
        mock_session.execute = AsyncMock(return_value=execute_result)

        service = ScimService(
            workspace_repo=MagicMock(),
            user_repo=MagicMock(),
            supabase_admin_client=MagicMock(),
        )

        token = await service.generate_scim_token(
            workspace_id=workspace.id,
            db=mock_session,
        )

        assert len(token) > 20
        expected_hash = hashlib.sha256(token.encode()).hexdigest()
        assert workspace.settings["scim_token_hash"] == expected_hash

    @pytest.mark.asyncio
    async def test_generate_token_workspace_not_found_raises(self) -> None:
        """generate_scim_token raises ScimWorkspaceNotFoundError when workspace not found."""
        from pilot_space.application.services.scim_service import (
            ScimService,
            ScimWorkspaceNotFoundError,
        )

        mock_session = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=execute_result)

        service = ScimService(
            workspace_repo=MagicMock(),
            user_repo=MagicMock(),
            supabase_admin_client=MagicMock(),
        )

        with pytest.raises(ScimWorkspaceNotFoundError, match="Workspace not found"):
            await service.generate_scim_token(
                workspace_id=uuid4(),
                db=mock_session,
            )


class TestScimRouterBearerAuth:
    """Tests for SCIM bearer token authentication."""

    @pytest.mark.asyncio
    async def test_missing_bearer_returns_401(self) -> None:
        """GET /scim/v2/{slug}/Users without Authorization returns 401."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from pilot_space.api.v1.routers.scim import router as scim_router

        app = FastAPI()
        app.include_router(scim_router, prefix="/api/v1")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/scim/v2/my-workspace/Users")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_bearer_returns_401(self) -> None:
        """GET /scim/v2/{slug}/Users with wrong token returns 401."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from pilot_space.api.v1.routers.scim import router as scim_router

        app = FastAPI()
        app.include_router(scim_router, prefix="/api/v1")

        workspace = _make_workspace(
            slug="test-ws",
            scim_token_hash=hashlib.sha256(b"correct-token").hexdigest(),
        )

        with patch(
            "pilot_space.api.v1.routers.scim._get_workspace_by_slug",
            AsyncMock(return_value=workspace),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/v1/scim/v2/test-ws/Users",
                    headers={"Authorization": "Bearer wrong-token"},
                )

        assert response.status_code == 401


class TestScimRouterListUsers:
    """Tests for GET /scim/v2/{slug}/Users."""

    @pytest.mark.asyncio
    async def test_list_users_returns_scim_list_response(self) -> None:
        """GET /Users returns a valid SCIM ListResponse with Resources array."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from pilot_space.api.v1.routers.scim import router as scim_router

        app = FastAPI()
        app.include_router(scim_router, prefix="/api/v1")

        workspace_id = uuid4()
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        workspace = _make_workspace(slug="test-ws", scim_token_hash=token_hash)
        workspace.id = workspace_id

        member1 = _make_member(workspace_id=workspace_id, email="a@example.com")
        member2 = _make_member(workspace_id=workspace_id, email="b@example.com")

        mock_service = MagicMock()
        mock_service.list_users = AsyncMock(return_value=([member1, member2], 2))

        with (
            patch(
                "pilot_space.api.v1.routers.scim._get_workspace_by_slug",
                AsyncMock(return_value=workspace),
            ),
            patch(
                "pilot_space.api.v1.routers.scim.get_scim_service",
                return_value=mock_service,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/v1/scim/v2/test-ws/Users",
                    headers={"Authorization": f"Bearer {raw_token}"},
                )

        assert response.status_code == 200
        body = response.json()
        assert body["totalResults"] == 2
        assert len(body["Resources"]) == 2

    @pytest.mark.asyncio
    async def test_list_users_pagination(self) -> None:
        """GET /Users?startIndex=2&count=1 returns correct slice."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from pilot_space.api.v1.routers.scim import router as scim_router

        app = FastAPI()
        app.include_router(scim_router, prefix="/api/v1")

        workspace_id = uuid4()
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        workspace = _make_workspace(slug="test-ws2", scim_token_hash=token_hash)
        workspace.id = workspace_id

        member2 = _make_member(workspace_id=workspace_id, email="b@example.com")

        mock_service = MagicMock()
        mock_service.list_users = AsyncMock(return_value=([member2], 2))

        with (
            patch(
                "pilot_space.api.v1.routers.scim._get_workspace_by_slug",
                AsyncMock(return_value=workspace),
            ),
            patch(
                "pilot_space.api.v1.routers.scim.get_scim_service",
                return_value=mock_service,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/v1/scim/v2/test-ws2/Users?startIndex=2&count=1",
                    headers={"Authorization": f"Bearer {raw_token}"},
                )

        assert response.status_code == 200
        body = response.json()
        assert body["totalResults"] == 2
        assert body["startIndex"] == 2
        assert body["itemsPerPage"] == 1
        assert len(body["Resources"]) == 1

        mock_service.list_users.assert_called_once()
        call_kwargs = mock_service.list_users.call_args
        assert call_kwargs.kwargs.get("start_index") == 2 or call_kwargs.args[1] == 2


class TestScimRouterServiceProviderConfig:
    """Tests for GET /scim/v2/{slug}/ServiceProviderConfig."""

    @pytest.mark.asyncio
    async def test_service_provider_config_no_auth_required(self) -> None:
        """GET /ServiceProviderConfig returns 200 without a bearer token."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from pilot_space.api.v1.routers.scim import router as scim_router

        app = FastAPI()
        app.include_router(scim_router, prefix="/api/v1")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/scim/v2/any-workspace/ServiceProviderConfig")

        assert response.status_code == 200
        body = response.json()
        assert "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig" in body["schemas"]
        assert body["patch"]["supported"] is True
        assert body["bulk"]["supported"] is False


class TestScimTokenEndpoint:
    """Tests for POST /api/v1/workspaces/{slug}/settings/scim-token (AUTH-07 gap)."""

    @pytest.mark.asyncio
    async def test_scim_token_endpoint_calls_service(self) -> None:
        """POST /settings/scim-token calls generate_scim_token and commits session."""
        import uuid as _uuid
        from unittest.mock import AsyncMock, MagicMock, patch

        from pilot_space.api.v1.routers.workspace_scim_settings import generate_scim_token

        fake_token = "raw_token_43chars_urlsafe"
        fake_workspace = MagicMock()
        fake_workspace.id = _uuid.uuid4()
        fake_workspace.slug = "acme"

        mock_session = AsyncMock()
        mock_service = AsyncMock()
        mock_service.generate_scim_token.return_value = fake_token

        with (
            patch(
                "pilot_space.api.v1.routers.workspace_scim_settings._resolve_workspace_scim",
                new=AsyncMock(return_value=fake_workspace),
            ),
            patch(
                "pilot_space.api.v1.routers.workspace_scim_settings.get_scim_service",
                return_value=mock_service,
            ),
        ):
            result = await generate_scim_token(
                workspace_slug="acme",
                session=mock_session,
                current_user=MagicMock(user_id=_uuid.uuid4()),
            )

        assert result == {"token": fake_token}
        mock_service.generate_scim_token.assert_awaited_once_with(
            workspace_id=fake_workspace.id, db=mock_session
        )
        mock_session.commit.assert_awaited_once()
