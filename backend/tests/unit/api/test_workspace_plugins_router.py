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


def _mock_workspace_token():
    """Patch _get_workspace_token to return None (system token)."""
    return patch(
        "pilot_space.api.v1.routers.workspace_plugins._get_workspace_token",
        new_callable=AsyncMock,
        return_value=None,
    )


async def test_browse_repo_returns_skill_list() -> None:
    """SKRG-01: GET /plugins/browse returns list of available skills from repo."""
    app, _ = _create_test_app()

    with (
        _mock_admin_check(),
        _mock_rls_context(),
        _mock_workspace_token(),
        patch(
            "pilot_space.integrations.github.plugin_service.GitHubPluginService",
            autospec=False,
        ) as MockGH,
    ):
        from pilot_space.integrations.github.plugin_service import SkillContent

        mock_gh = MagicMock()
        MockGH.return_value = mock_gh
        mock_gh.list_skills = AsyncMock(return_value=["mcp-builder", "claude-api"])
        mock_gh.fetch_skill_content = AsyncMock(
            return_value=SkillContent(
                skill_md="---\nname: test\n---\n# Test",
                references=[],
                display_name="Test",
                description="A test skill",
            )
        )
        mock_gh.aclose = AsyncMock()

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

    with (
        _mock_admin_check(),
        _mock_rls_context(),
        _mock_workspace_token(),
        patch(
            "pilot_space.integrations.github.plugin_service.GitHubPluginService",
            autospec=False,
        ) as MockGH,
    ):
        from pilot_space.integrations.github.plugin_service import PluginRateLimitError

        mock_gh = MagicMock()
        MockGH.return_value = mock_gh
        mock_gh.list_skills = AsyncMock(side_effect=PluginRateLimitError("Rate limit exceeded"))
        mock_gh.aclose = AsyncMock()

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

    # Override Redis dependency
    from pilot_space.dependencies.ai import get_redis_client

    mock_redis = AsyncMock()
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

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

    with (
        _mock_admin_check(),
        _mock_rls_context(),
        _mock_workspace_token(),
        patch(
            "pilot_space.infrastructure.database.repositories.workspace_plugin_repository.WorkspacePluginRepository"
        ) as MockRepo,
        patch(
            "pilot_space.api.v1.routers.workspace_plugins._get_cached_head_sha",
            new_callable=AsyncMock,
            return_value="b" * 40,
        ),
    ):
        mock_repo = MockRepo.return_value
        mock_repo.get_installed_by_workspace = AsyncMock(return_value=[mock_plugin])

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
    """SKRG-04: update check uses Redis cache."""
    app, _ = _create_test_app()

    from pilot_space.dependencies.ai import get_redis_client

    mock_redis = AsyncMock()
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

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

    cached_sha = "c" * 40

    with (
        _mock_admin_check(),
        _mock_rls_context(),
        _mock_workspace_token(),
        patch(
            "pilot_space.infrastructure.database.repositories.workspace_plugin_repository.WorkspacePluginRepository"
        ) as MockRepo,
        patch(
            "pilot_space.api.v1.routers.workspace_plugins._get_cached_head_sha",
            new_callable=AsyncMock,
            return_value=cached_sha,
        ) as mock_cache,
    ):
        mock_repo = MockRepo.return_value
        mock_repo.get_installed_by_workspace = AsyncMock(return_value=[mock_plugin])

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/plugins/check-updates",
            )

    assert resp.status_code == 200
    mock_cache.assert_awaited_once()
