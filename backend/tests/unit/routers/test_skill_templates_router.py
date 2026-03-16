"""Unit tests for skill templates router.

Tests verify:
- GET list returns templates for all members
- POST create returns 201 (admin only)
- PATCH update returns 200 (admin only, built-in guard)
- DELETE returns 204 (admin only)
- 403 for non-admin on mutations
- 404 for missing template on PATCH/DELETE
- 403 when editing built-in template fields other than is_active

Source: Phase 20, P20-05
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.infrastructure.auth.supabase_auth import TokenPayload
from pilot_space.infrastructure.database.models.skill_template import SkillTemplate

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKSPACE_ID = uuid4()
USER_ID = uuid4()
TEMPLATE_ID = uuid4()
BASE_URL = f"http://test/api/v1/workspaces/{WORKSPACE_ID}/skill-templates"


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


def _make_template(
    *,
    template_id: str | None = None,
    name: str = "Backend Engineer",
    source: str = "workspace",
    is_active: bool = True,
    is_deleted: bool = False,
    sort_order: int = 0,
) -> MagicMock:
    """Create a minimal SkillTemplate-like mock."""
    tmpl = MagicMock(spec=SkillTemplate)
    tmpl.id = template_id or uuid4()
    tmpl.workspace_id = WORKSPACE_ID
    tmpl.name = name
    tmpl.description = "A backend skill"
    tmpl.skill_content = "# Backend\nYou are a backend engineer."
    tmpl.icon = "Code"
    tmpl.sort_order = sort_order
    tmpl.source = source
    tmpl.role_type = None
    tmpl.is_active = is_active
    tmpl.is_deleted = is_deleted
    tmpl.created_by = USER_ID
    tmpl.created_at = datetime.now(tz=UTC)
    tmpl.updated_at = datetime.now(tz=UTC)
    return tmpl


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with auth + admin guard mocked + workspace header."""
    from pilot_space.dependencies.auth import get_current_user
    from pilot_space.main import app

    token_payload = _make_token_payload()
    app.dependency_overrides[get_current_user] = lambda: token_payload

    with (
        patch(
            "pilot_space.api.v1.routers.skill_templates._require_admin",
            new=AsyncMock(),
        ),
        patch(
            "pilot_space.api.v1.routers.skill_templates.set_rls_context",
            new=AsyncMock(),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={
                "Authorization": "Bearer test-token",
                "X-Workspace-ID": str(WORKSPACE_ID),
            },
        ) as client:
            yield client

    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def non_admin_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with auth but admin guard raises 403."""
    from fastapi import HTTPException, status

    from pilot_space.dependencies.auth import get_current_user
    from pilot_space.main import app

    token_payload = _make_token_payload()
    app.dependency_overrides[get_current_user] = lambda: token_payload

    async def _raise_403(*args: object, **kwargs: object) -> None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner role required",
        )

    with (
        patch(
            "pilot_space.api.v1.routers.skill_templates._require_admin",
            new=AsyncMock(side_effect=_raise_403),
        ),
        patch(
            "pilot_space.api.v1.routers.skill_templates.set_rls_context",
            new=AsyncMock(),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={
                "Authorization": "Bearer test-token",
                "X-Workspace-ID": str(WORKSPACE_ID),
            },
        ) as client:
            yield client

    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# GET /skill-templates
# ---------------------------------------------------------------------------


async def test_list_templates_returns_200(admin_client: AsyncClient) -> None:
    """GET returns list of templates for workspace."""
    mock_template = _make_template()

    with patch(
        "pilot_space.api.v1.routers.skill_templates.SkillTemplateRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_workspace = AsyncMock(return_value=[mock_template])

        resp = await admin_client.get(BASE_URL)

    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Backend Engineer"


async def test_list_templates_empty(admin_client: AsyncClient) -> None:
    """GET returns empty list when no templates exist."""
    with patch(
        "pilot_space.api.v1.routers.skill_templates.SkillTemplateRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_workspace = AsyncMock(return_value=[])

        resp = await admin_client.get(BASE_URL)

    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /skill-templates
# ---------------------------------------------------------------------------


async def test_create_template_returns_201(admin_client: AsyncClient) -> None:
    """POST creates a workspace template with source='workspace'."""
    mock_template = _make_template(name="DevOps Engineer")

    with patch(
        "pilot_space.api.v1.routers.skill_templates.SkillTemplateRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.create = AsyncMock(return_value=mock_template)

        resp = await admin_client.post(
            BASE_URL,
            json={
                "name": "DevOps Engineer",
                "description": "A devops skill",
                "skill_content": "# DevOps\nYou are a devops engineer.",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "DevOps Engineer"
    # Verify source='workspace' was passed to create
    mock_repo.create.assert_called_once()
    call_kwargs = mock_repo.create.call_args.kwargs
    assert call_kwargs["source"] == "workspace"


async def test_create_template_403_non_admin(non_admin_client: AsyncClient) -> None:
    """POST returns 403 for non-admin users."""
    resp = await non_admin_client.post(
        BASE_URL,
        json={
            "name": "Nope",
            "description": "Nope",
            "skill_content": "# Nope",
        },
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /skill-templates/{template_id}
# ---------------------------------------------------------------------------


async def test_update_template_returns_200(admin_client: AsyncClient) -> None:
    """PATCH updates a workspace template."""
    mock_template = _make_template(template_id=str(TEMPLATE_ID))
    updated_template = _make_template(template_id=str(TEMPLATE_ID), name="Updated Name")

    with patch(
        "pilot_space.api.v1.routers.skill_templates.SkillTemplateRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id = AsyncMock(return_value=mock_template)
        mock_repo.update = AsyncMock(return_value=updated_template)

        resp = await admin_client.patch(
            f"{BASE_URL}/{TEMPLATE_ID}",
            json={"name": "Updated Name"},
        )

    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


async def test_update_template_404_not_found(admin_client: AsyncClient) -> None:
    """PATCH returns 404 when template not found."""
    with patch(
        "pilot_space.api.v1.routers.skill_templates.SkillTemplateRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id = AsyncMock(return_value=None)

        resp = await admin_client.patch(
            f"{BASE_URL}/{TEMPLATE_ID}",
            json={"name": "Updated Name"},
        )

    assert resp.status_code == 404


async def test_update_built_in_only_is_active(admin_client: AsyncClient) -> None:
    """PATCH on built-in template allows is_active toggle only."""
    mock_template = _make_template(source="built_in")

    with patch(
        "pilot_space.api.v1.routers.skill_templates.SkillTemplateRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id = AsyncMock(return_value=mock_template)
        mock_repo.update = AsyncMock(return_value=mock_template)

        # Toggling is_active should succeed
        resp = await admin_client.patch(
            f"{BASE_URL}/{TEMPLATE_ID}",
            json={"is_active": False},
        )
        assert resp.status_code == 200


async def test_update_built_in_rejects_other_fields(
    admin_client: AsyncClient,
) -> None:
    """PATCH on built-in template rejects changes to name/description/etc."""
    mock_template = _make_template(source="built_in")

    with patch(
        "pilot_space.api.v1.routers.skill_templates.SkillTemplateRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id = AsyncMock(return_value=mock_template)

        resp = await admin_client.patch(
            f"{BASE_URL}/{TEMPLATE_ID}",
            json={"name": "Hacked Name"},
        )
        assert resp.status_code == 403
        assert "Built-in" in resp.json()["detail"]


async def test_update_template_403_non_admin(non_admin_client: AsyncClient) -> None:
    """PATCH returns 403 for non-admin."""
    resp = await non_admin_client.patch(
        f"{BASE_URL}/{TEMPLATE_ID}",
        json={"name": "Updated"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /skill-templates/{template_id}
# ---------------------------------------------------------------------------


async def test_delete_template_returns_204(admin_client: AsyncClient) -> None:
    """DELETE soft-deletes a template."""
    mock_template = _make_template()

    with patch(
        "pilot_space.api.v1.routers.skill_templates.SkillTemplateRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.soft_delete = AsyncMock(return_value=mock_template)

        resp = await admin_client.delete(f"{BASE_URL}/{TEMPLATE_ID}")

    assert resp.status_code == 204


async def test_delete_template_404_not_found(admin_client: AsyncClient) -> None:
    """DELETE returns 404 when template not found."""
    with patch(
        "pilot_space.api.v1.routers.skill_templates.SkillTemplateRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.soft_delete = AsyncMock(return_value=None)

        resp = await admin_client.delete(f"{BASE_URL}/{TEMPLATE_ID}")

    assert resp.status_code == 404


async def test_delete_template_403_non_admin(non_admin_client: AsyncClient) -> None:
    """DELETE returns 403 for non-admin."""
    resp = await non_admin_client.delete(f"{BASE_URL}/{TEMPLATE_ID}")
    assert resp.status_code == 403
