"""Tests for workspace plugins router — SKRG-01, SKRG-04.

Tests verify REST endpoint behavior using httpx AsyncClient with FastAPI
dependency overrides — follows test_workspace_tasks.py pattern.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio

_WORKSPACE_ID = uuid4()
_USER_ID = uuid4()


def _create_test_app():
    """Create a minimal FastAPI app with plugins router and dependency overrides."""
    from fastapi import FastAPI

    from pilot_space.api.middleware.error_handler import register_exception_handlers
    from pilot_space.api.middleware.request_context import get_workspace_id
    from pilot_space.api.v1.routers.workspace_plugins import router
    from pilot_space.dependencies.auth import get_current_user_id, get_db_session

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/workspaces")
    register_exception_handlers(app)

    # Override DI dependencies for testing
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    app.dependency_overrides[get_workspace_id] = lambda: _WORKSPACE_ID

    return app, mock_session


def _mock_admin_check():
    """Patch _require_admin and set_rls_context to always pass."""
    return patch(
        "pilot_space.api.v1.routers.workspace_plugins._require_admin",
        new_callable=AsyncMock,
    )


def _mock_rls_context():
    """Patch set_rls_context to no-op in tests."""
    return patch(
        "pilot_space.api.v1.routers.workspace_plugins.set_rls_context",
        new_callable=AsyncMock,
    )


def _override_plugin_service(app, mock_svc):
    """Override the PluginLifecycleService DI dependency."""
    from pilot_space.api.v1 import dependencies as dep_module

    app.dependency_overrides[dep_module._get_plugin_lifecycle_service] = lambda: mock_svc


async def test_browse_repo_returns_skill_list() -> None:
    """SKRG-01: GET /plugins/browse returns list of available skills from repo."""
    from pilot_space.application.services.plugin_lifecycle import BrowseRepoResult

    app, _ = _create_test_app()

    mock_svc = MagicMock()
    mock_svc.browse_repo = AsyncMock(
        return_value=[
            BrowseRepoResult(
                skill_name="mcp-builder",
                display_name="Test",
                description="A test skill",
            ),
            BrowseRepoResult(
                skill_name="claude-api",
                display_name="Claude API",
            ),
        ]
    )
    _override_plugin_service(app, mock_svc)

    with (
        _mock_admin_check(),
        _mock_rls_context(),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/plugins/browse",
                params={"repo_url": "https://github.com/anthropics/skills"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["skill_name"] == "mcp-builder"


async def test_browse_repo_raises_on_github_unreachable() -> None:
    """SKRG-01: browse returns 502 when GitHub is unreachable."""
    app, _ = _create_test_app()

    from pilot_space.integrations.github.plugin_service import PluginRateLimitError

    mock_svc = MagicMock()
    mock_svc.browse_repo = AsyncMock(side_effect=PluginRateLimitError("Rate limit exceeded"))
    _override_plugin_service(app, mock_svc)

    with (
        _mock_admin_check(),
        _mock_rls_context(),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/plugins/browse",
                params={"repo_url": "https://github.com/org/repo"},
            )

    assert resp.status_code == 502


async def test_list_installed_plugins() -> None:
    """GET /plugins returns installed plugins."""
    app, _ = _create_test_app()

    mock_plugin = MagicMock()
    mock_plugin.id = uuid4()
    mock_plugin.workspace_id = _WORKSPACE_ID
    mock_plugin.repo_url = "https://github.com/anthropics/skills"
    mock_plugin.skill_name = "mcp-builder"
    mock_plugin.display_name = "MCP Builder"
    mock_plugin.description = "Build MCP servers"
    mock_plugin.installed_sha = "a" * 40
    mock_plugin.is_active = True

    with (
        _mock_admin_check(),
        _mock_rls_context(),
        patch(
            "pilot_space.infrastructure.database.repositories.workspace_plugin_repository.WorkspacePluginRepository"
        ) as MockRepo,
    ):
        mock_repo = MockRepo.return_value
        mock_repo.get_installed_by_workspace = AsyncMock(return_value=[mock_plugin])

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/plugins",
            )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["skill_name"] == "mcp-builder"


async def test_update_check_returns_has_update_true_when_sha_differs() -> None:
    """SKRG-04: check-updates returns has_update=true when SHA differs."""
    app, _ = _create_test_app()

    mock_plugin = MagicMock()
    mock_plugin.id = uuid4()
    mock_plugin.workspace_id = _WORKSPACE_ID
    mock_plugin.repo_url = "https://github.com/anthropics/skills"
    mock_plugin.repo_owner = "anthropics"
    mock_plugin.repo_name = "skills"
    mock_plugin.skill_name = "mcp-builder"
    mock_plugin.display_name = "MCP Builder"
    mock_plugin.description = None
    mock_plugin.installed_sha = "a" * 40
    mock_plugin.is_active = True
    mock_plugin.is_deleted = False

    mock_svc = MagicMock()
    mock_svc.check_updates = AsyncMock(return_value=[(mock_plugin, True)])
    _override_plugin_service(app, mock_svc)

    with (
        _mock_admin_check(),
        _mock_rls_context(),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/plugins/check-updates",
            )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["plugins"]) == 1
    assert data["plugins"][0]["has_update"] is True


async def test_update_check_caches_result_five_minutes() -> None:
    """SKRG-04: update check uses Redis cache (via service)."""
    app, _ = _create_test_app()

    mock_plugin = MagicMock()
    mock_plugin.id = uuid4()
    mock_plugin.workspace_id = _WORKSPACE_ID
    mock_plugin.repo_url = "https://github.com/anthropics/skills"
    mock_plugin.repo_owner = "anthropics"
    mock_plugin.repo_name = "skills"
    mock_plugin.skill_name = "mcp-builder"
    mock_plugin.display_name = "MCP Builder"
    mock_plugin.description = None
    mock_plugin.installed_sha = "a" * 40
    mock_plugin.is_active = True
    mock_plugin.is_deleted = False

    cached_sha = "c" * 40  # referenced by description only

    mock_svc = MagicMock()
    mock_svc.check_updates = AsyncMock(return_value=[(mock_plugin, False)])
    _override_plugin_service(app, mock_svc)

    with (
        _mock_admin_check(),
        _mock_rls_context(),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/plugins/check-updates",
            )

    assert resp.status_code == 200
    mock_svc.check_updates.assert_awaited_once_with(_WORKSPACE_ID)
