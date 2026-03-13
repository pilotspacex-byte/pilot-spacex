"""Unit tests for workspace action buttons router.

Tests verify:
- Admin guard returns 403 for non-admin
- GET list returns active buttons for all members
- GET admin returns all buttons for admins
- POST create returns 201
- PATCH update returns updated button
- PUT reorder returns 204
- DELETE returns 204

Source: Phase 17, SKBTN-01..04
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.infrastructure.auth.supabase_auth import TokenPayload
from pilot_space.infrastructure.database.models.skill_action_button import (
    BindingType,
    SkillActionButton,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKSPACE_ID = uuid4()
USER_ID = uuid4()
BUTTON_ID = uuid4()
BASE_URL = f"http://test/api/v1/workspaces/{WORKSPACE_ID}/action-buttons"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token_payload() -> TokenPayload:
    """Build a minimal TokenPayload for auth override."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub=str(USER_ID),
        email="test@example.com",
        role="authenticated",
        aud="authenticated",
        exp=int(now.timestamp()) + 3600,
        iat=int(now.timestamp()),
        app_metadata={},
        user_metadata={},
    )


def _make_button(
    *,
    button_id: str | None = None,
    name: str = "Run Tests",
    binding_type: BindingType = BindingType.SKILL,
    sort_order: int = 0,
    is_active: bool = True,
) -> MagicMock:
    """Create a minimal SkillActionButton-like mock."""
    btn = MagicMock(spec=SkillActionButton)
    btn.id = button_id or uuid4()
    btn.workspace_id = WORKSPACE_ID
    btn.name = name
    btn.icon = "play"
    btn.binding_type = binding_type
    btn.binding_id = None
    btn.binding_metadata = {}
    btn.sort_order = sort_order
    btn.is_active = is_active
    btn.is_deleted = False
    btn.created_at = datetime.now(tz=UTC)
    btn.updated_at = datetime.now(tz=UTC)
    return btn


@pytest.fixture
async def admin_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with auth + admin guard mocked."""
    from pilot_space.api.middleware.request_context import get_workspace_id
    from pilot_space.dependencies.auth import get_current_user
    from pilot_space.main import app

    token_payload = _make_token_payload()
    app.dependency_overrides[get_current_user] = lambda: token_payload
    app.dependency_overrides[get_workspace_id] = lambda: WORKSPACE_ID

    with (
        patch(
            "pilot_space.api.v1.routers.workspace_action_buttons._require_admin",
            new=AsyncMock(),
        ),
        patch(
            "pilot_space.api.v1.routers.workspace_action_buttons._require_member",
            new=AsyncMock(),
        ),
        patch(
            "pilot_space.api.v1.routers.workspace_action_buttons.set_rls_context",
            new=AsyncMock(),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as client:
            yield client

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_workspace_id, None)


@pytest.fixture
async def non_admin_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with auth but admin guard raises 403."""
    from fastapi import HTTPException, status

    from pilot_space.api.middleware.request_context import get_workspace_id
    from pilot_space.dependencies.auth import get_current_user
    from pilot_space.main import app

    token_payload = _make_token_payload()
    app.dependency_overrides[get_current_user] = lambda: token_payload
    app.dependency_overrides[get_workspace_id] = lambda: WORKSPACE_ID

    async def _reject_admin(*args: object, **kwargs: object) -> None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    with (
        patch(
            "pilot_space.api.v1.routers.workspace_action_buttons._require_admin",
            new=_reject_admin,
        ),
        patch(
            "pilot_space.api.v1.routers.workspace_action_buttons.set_rls_context",
            new=AsyncMock(),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as client:
            yield client

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_workspace_id, None)


# ---------------------------------------------------------------------------
# Tests: Admin guard
# ---------------------------------------------------------------------------


class TestAdminGuard:
    """Test admin guard rejects non-admin users on write endpoints."""

    async def test_post_requires_admin(self, non_admin_client: AsyncClient) -> None:
        """POST create returns 403 for non-admin."""
        resp = await non_admin_client.post(
            BASE_URL,
            json={"name": "Test", "binding_type": "skill"},
        )
        assert resp.status_code == 403

    async def test_delete_requires_admin(self, non_admin_client: AsyncClient) -> None:
        """DELETE returns 403 for non-admin."""
        resp = await non_admin_client.delete(f"{BASE_URL}/{uuid4()}")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: CRUD operations
# ---------------------------------------------------------------------------


class TestListActiveButtons:
    """Test GET active buttons list."""

    async def test_returns_active_buttons(self, admin_client: AsyncClient) -> None:
        """GET list returns active buttons as list."""
        buttons = [_make_button(), _make_button(name="Deploy")]
        with patch(
            "pilot_space.api.v1.routers.workspace_action_buttons.SkillActionButtonRepository",
        ) as MockRepo:
            mock_instance = MockRepo.return_value
            mock_instance.get_active_by_workspace = AsyncMock(return_value=buttons)
            resp = await admin_client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2


class TestListAdminButtons:
    """Test GET admin buttons list."""

    async def test_returns_all_buttons(self, admin_client: AsyncClient) -> None:
        """GET /admin returns all buttons including inactive."""
        buttons = [_make_button(), _make_button(name="Inactive", is_active=False)]
        with patch(
            "pilot_space.api.v1.routers.workspace_action_buttons.SkillActionButtonRepository",
        ) as MockRepo:
            mock_instance = MockRepo.return_value
            mock_instance.get_all_by_workspace = AsyncMock(return_value=buttons)
            resp = await admin_client.get(f"{BASE_URL}/admin")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


class TestCreateButton:
    """Test POST create button."""

    async def test_creates_button(self, admin_client: AsyncClient) -> None:
        """POST creates a button and returns 201."""
        new_button = _make_button()
        with patch(
            "pilot_space.api.v1.routers.workspace_action_buttons.SkillActionButtonRepository",
        ) as MockRepo:
            mock_instance = MockRepo.return_value
            mock_instance.create = AsyncMock(return_value=new_button)
            resp = await admin_client.post(
                BASE_URL,
                json={
                    "name": "Run Tests",
                    "binding_type": "skill",
                    "icon": "play",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Run Tests"


class TestUpdateButton:
    """Test PATCH update button."""

    async def test_updates_button(self, admin_client: AsyncClient) -> None:
        """PATCH updates a button and returns 200."""
        existing = _make_button(button_id=str(BUTTON_ID))
        updated = _make_button(button_id=str(BUTTON_ID), name="Updated")
        with patch(
            "pilot_space.api.v1.routers.workspace_action_buttons.SkillActionButtonRepository",
        ) as MockRepo:
            mock_instance = MockRepo.return_value
            mock_instance.get_by_workspace_and_id = AsyncMock(return_value=existing)
            mock_instance.update = AsyncMock(return_value=updated)
            resp = await admin_client.patch(
                f"{BASE_URL}/{BUTTON_ID}",
                json={"name": "Updated"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated"

    async def test_update_not_found(self, admin_client: AsyncClient) -> None:
        """PATCH returns 404 when button not found."""
        with patch(
            "pilot_space.api.v1.routers.workspace_action_buttons.SkillActionButtonRepository",
        ) as MockRepo:
            mock_instance = MockRepo.return_value
            mock_instance.get_by_workspace_and_id = AsyncMock(return_value=None)
            resp = await admin_client.patch(
                f"{BASE_URL}/{uuid4()}",
                json={"name": "Updated"},
            )
        assert resp.status_code == 404


class TestReorderButtons:
    """Test PUT reorder buttons."""

    async def test_reorders_buttons(self, admin_client: AsyncClient) -> None:
        """PUT reorder returns 204."""
        ids = [uuid4(), uuid4(), uuid4()]
        buttons = [_make_button(button_id=str(bid)) for bid in ids]
        # Map button.id to button for the dict lookup in reorder
        for btn, bid in zip(buttons, ids, strict=True):
            btn.id = bid
        with patch(
            "pilot_space.api.v1.routers.workspace_action_buttons.SkillActionButtonRepository",
        ) as MockRepo:
            mock_instance = MockRepo.return_value
            mock_instance.get_all_by_workspace = AsyncMock(return_value=buttons)
            resp = await admin_client.put(
                f"{BASE_URL}/reorder",
                json={"button_ids": [str(bid) for bid in ids]},
            )
        assert resp.status_code == 204


class TestDeleteButton:
    """Test DELETE button."""

    async def test_deletes_button(self, admin_client: AsyncClient) -> None:
        """DELETE returns 204."""
        existing = _make_button(button_id=str(BUTTON_ID))
        with patch(
            "pilot_space.api.v1.routers.workspace_action_buttons.SkillActionButtonRepository",
        ) as MockRepo:
            mock_instance = MockRepo.return_value
            mock_instance.get_by_workspace_and_id = AsyncMock(return_value=existing)
            mock_instance.soft_delete = AsyncMock()
            resp = await admin_client.delete(f"{BASE_URL}/{BUTTON_ID}")
        assert resp.status_code == 204

    async def test_delete_not_found(self, admin_client: AsyncClient) -> None:
        """DELETE returns 404 when button not found."""
        with patch(
            "pilot_space.api.v1.routers.workspace_action_buttons.SkillActionButtonRepository",
        ) as MockRepo:
            mock_instance = MockRepo.return_value
            mock_instance.get_by_workspace_and_id = AsyncMock(return_value=None)
            resp = await admin_client.delete(f"{BASE_URL}/{uuid4()}")
        assert resp.status_code == 404
