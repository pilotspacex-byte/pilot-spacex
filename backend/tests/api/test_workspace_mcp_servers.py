"""Tests for workspace MCP server CRUD and agent wiring (Phase 14).

Covers MCP-01 through MCP-06:
  MCP-01: POST creates registered server row (admin-only)
  MCP-02: Bearer token stored encrypted at rest
  MCP-03: OAuth callback stores token after code exchange
  MCP-05: Status endpoint returns connected/failed/unknown
  MCP-06: DELETE soft-deletes; subsequent GET excludes the server

These are Wave 0 test stubs. Each test is marked xfail(strict=False) so
the suite exits 0 while implementation is pending (phase 14 plans 02-03).
Tests bodies contain the minimal assertion shape that drives the green
implementation - they will become real assertions when the router is built.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Local fixture: workspace with an admin member for the test user
# ---------------------------------------------------------------------------


@pytest.fixture
async def mcp_workspace_with_admin(
    db_session: AsyncSession,
    test_user_id,  # UUID fixture from root conftest
) -> tuple[object, object]:
    """Create workspace + admin member used across MCP API tests."""
    from pilot_space.infrastructure.database.models import (
        Workspace,
        WorkspaceMember,
        WorkspaceRole,
    )

    workspace = Workspace(
        name="MCP Test Workspace",
        slug=f"mcp-test-{uuid4().hex[:8]}",
        owner_id=test_user_id,
    )
    db_session.add(workspace)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user_id,
        role=WorkspaceRole.ADMIN,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(workspace)

    return workspace, member


@pytest.fixture
async def mcp_workspace_with_member(
    db_session: AsyncSession,
    test_user_id,
) -> tuple[object, object]:
    """Create workspace with a non-admin MEMBER for 403 tests."""
    from pilot_space.infrastructure.database.models import (
        Workspace,
        WorkspaceMember,
        WorkspaceRole,
    )

    workspace = Workspace(
        name="MCP Member Workspace",
        slug=f"mcp-member-{uuid4().hex[:8]}",
        owner_id=uuid4(),  # Different owner
    )
    db_session.add(workspace)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user_id,
        role=WorkspaceRole.MEMBER,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(workspace)

    return workspace, member


# ---------------------------------------------------------------------------
# MCP-01: Register a server
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="implementation pending — phase 14 plan 02/03")
async def test_register_server(
    authenticated_client: AsyncClient,
    mcp_workspace_with_admin,
    db_session: AsyncSession,
) -> None:
    """MCP-01: POST /workspaces/{id}/mcp-servers creates a server row and returns 201.

    Expected response shape:
        {
            "id": "<uuid>",
            "display_name": "My MCP Server",
            "url": "https://mcp.example.com/sse",
            "auth_type": "bearer",
            "last_status": null,
            "created_at": "<iso8601>"
        }
    """
    workspace, _ = mcp_workspace_with_admin
    payload = {
        "display_name": "My MCP Server",
        "url": "https://mcp.example.com/sse",
        "auth_type": "bearer",
        "auth_token": "sk-test-token",
    }

    response = await authenticated_client.post(
        f"/api/v1/workspaces/{workspace.id}/mcp-servers",
        json=payload,
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["display_name"] == "My MCP Server"
    assert data["url"] == "https://mcp.example.com/sse"
    assert data["auth_type"] == "bearer"
    # Token MUST NOT be echoed back in response
    assert "auth_token" not in data
    assert "auth_token_encrypted" not in data


# ---------------------------------------------------------------------------
# MCP-02: Token encrypted at rest
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="implementation pending — phase 14 plan 02/03")
async def test_token_encrypted_at_rest(
    authenticated_client: AsyncClient,
    mcp_workspace_with_admin,
    db_session: AsyncSession,
) -> None:
    """MCP-02: Bearer token is stored encrypted; DB column != plaintext.

    After a successful POST, a direct DB query on workspace_mcp_servers
    confirms auth_token_encrypted is NOT equal to the submitted plaintext token.
    The encrypted value must be a non-empty string (Fernet ciphertext starts with 'gAAAAA').
    """
    from sqlalchemy import select

    workspace, _ = mcp_workspace_with_admin
    plain_token = "sk-plaintext-secret-token"

    response = await authenticated_client.post(
        f"/api/v1/workspaces/{workspace.id}/mcp-servers",
        json={
            "display_name": "Encrypted Token Server",
            "url": "https://mcp.example.com/sse",
            "auth_type": "bearer",
            "auth_token": plain_token,
        },
    )
    assert response.status_code == 201
    server_id = response.json()["id"]

    # Import only inside test body so xfail isolation works — import fails until
    # the model is created in plan 14-02, which is the correct RED state.
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        WorkspaceMcpServer,
    )

    stmt = select(WorkspaceMcpServer).where(WorkspaceMcpServer.id == server_id)
    result = await db_session.execute(stmt)
    row = result.scalar_one()

    assert row.auth_token_encrypted is not None
    assert row.auth_token_encrypted != plain_token
    # Fernet ciphertext is base64url and starts with gAAAAA (version byte 0x80)
    assert len(row.auth_token_encrypted) > 40


# ---------------------------------------------------------------------------
# MCP-03: OAuth callback stores token
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="implementation pending — phase 14 plan 02/03")
async def test_oauth_callback_stores_token(
    authenticated_client: AsyncClient,
    mcp_workspace_with_admin,
    db_session: AsyncSession,
) -> None:
    """MCP-03: OAuth callback exchanges code and stores encrypted token.

    Flow:
      1. POST server with auth_type=oauth2 — returns auth_url for redirect.
      2. GET /api/v1/oauth2/mcp-callback?code=...&state=... — simulates provider
         callback; stores token encrypted in auth_token_encrypted.

    The mock code exchange should store a non-null auth_token_encrypted on the
    workspace_mcp_server row.
    """
    from sqlalchemy import select

    workspace, _ = mcp_workspace_with_admin

    # Step 1: Register OAuth server
    response = await authenticated_client.post(
        f"/api/v1/workspaces/{workspace.id}/mcp-servers",
        json={
            "display_name": "OAuth MCP Server",
            "url": "https://mcp.oauth.example.com/sse",
            "auth_type": "oauth2",
            "oauth_client_id": "client-abc",
            "oauth_auth_url": "https://auth.example.com/authorize",
            "oauth_token_url": "https://auth.example.com/token",
            "oauth_scopes": "read write",
        },
    )
    assert response.status_code == 201
    server_id = response.json()["id"]
    assert "auth_url" in response.json()  # Backend provides redirect URL

    # Step 2: Simulate OAuth callback (state is mcp_oauth_{server_id}_{nonce})
    # In a real test, state would come from Redis; here we assert the callback
    # endpoint is wired and stores the token.
    callback_response = await authenticated_client.get(
        "/api/v1/oauth2/mcp-callback",
        params={
            "code": "test-auth-code",
            "state": f"mcp_oauth_{server_id}_test-nonce",
        },
    )
    # Callback redirects (302) or returns 200 with confirmation
    assert callback_response.status_code in (200, 302)

    # Step 3: Verify token stored encrypted
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        WorkspaceMcpServer,
    )

    stmt = select(WorkspaceMcpServer).where(WorkspaceMcpServer.id == server_id)
    result = await db_session.execute(stmt)
    row = result.scalar_one()
    assert row.auth_token_encrypted is not None


# ---------------------------------------------------------------------------
# MCP-05: Status endpoint
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="implementation pending — phase 14 plan 02/03")
async def test_status_endpoint(
    authenticated_client: AsyncClient,
    mcp_workspace_with_admin,
    db_session: AsyncSession,
) -> None:
    """MCP-05: GET .../status returns JSON with status field.

    The status field must be one of: 'connected', 'failed', 'unknown'.
    In unit tests we mock httpx so the server is not actually contacted.
    """
    from unittest.mock import AsyncMock, patch

    workspace, _ = mcp_workspace_with_admin

    # First register a server to get a valid ID
    reg_response = await authenticated_client.post(
        f"/api/v1/workspaces/{workspace.id}/mcp-servers",
        json={
            "display_name": "Status Check Server",
            "url": "https://mcp.status.example.com/sse",
            "auth_type": "bearer",
            "auth_token": "sk-status-token",
        },
    )
    assert reg_response.status_code == 201
    server_id = reg_response.json()["id"]

    # Mock httpx to return 200 (connected)
    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client_instance

        status_response = await authenticated_client.get(
            f"/api/v1/workspaces/{workspace.id}/mcp-servers/{server_id}/status"
        )

    assert status_response.status_code == 200
    status_data = status_response.json()
    assert "status" in status_data
    assert status_data["status"] in ("connected", "failed", "unknown")


# ---------------------------------------------------------------------------
# MCP-06: DELETE removes server from list
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="implementation pending — phase 14 plan 02/03")
async def test_delete_removes_from_agent(
    authenticated_client: AsyncClient,
    mcp_workspace_with_admin,
    db_session: AsyncSession,
) -> None:
    """MCP-06: DELETE soft-deletes server; subsequent GET list excludes it.

    After DELETE 204, the server must not appear in GET /mcp-servers.
    The row is soft-deleted (is_deleted=True) not hard-deleted — DB record persists.
    """
    from sqlalchemy import select

    workspace, _ = mcp_workspace_with_admin

    # Register server
    reg_response = await authenticated_client.post(
        f"/api/v1/workspaces/{workspace.id}/mcp-servers",
        json={
            "display_name": "To Be Deleted",
            "url": "https://mcp.delete.example.com/sse",
            "auth_type": "bearer",
            "auth_token": "sk-delete-token",
        },
    )
    assert reg_response.status_code == 201
    server_id = reg_response.json()["id"]

    # Delete
    del_response = await authenticated_client.delete(
        f"/api/v1/workspaces/{workspace.id}/mcp-servers/{server_id}"
    )
    assert del_response.status_code == 204

    # Subsequent GET list excludes deleted server
    list_response = await authenticated_client.get(f"/api/v1/workspaces/{workspace.id}/mcp-servers")
    assert list_response.status_code == 200
    items = list_response.json().get("items", list_response.json())
    server_ids = [s["id"] for s in items]
    assert server_id not in server_ids

    # Verify soft-delete: DB row still exists with is_deleted=True
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        WorkspaceMcpServer,
    )

    stmt = select(WorkspaceMcpServer).where(WorkspaceMcpServer.id == server_id)
    result = await db_session.execute(stmt)
    row = result.scalar_one_or_none()
    # Row exists but is soft-deleted
    assert row is not None
    assert row.is_deleted is True


# ---------------------------------------------------------------------------
# MCP-01: Admin-only gate
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="implementation pending — phase 14 plan 02/03")
async def test_admin_only(
    authenticated_client: AsyncClient,
    mcp_workspace_with_member,
    db_session: AsyncSession,
) -> None:
    """MCP-01: Non-admin member calling POST → 403 Forbidden.

    The router must check OWNER/ADMIN role via _get_admin_workspace() pattern
    from workspace_ai_settings.py. A MEMBER role must be rejected.
    """
    workspace, _ = mcp_workspace_with_member

    response = await authenticated_client.post(
        f"/api/v1/workspaces/{workspace.id}/mcp-servers",
        json={
            "display_name": "Unauthorized Server",
            "url": "https://mcp.example.com/sse",
            "auth_type": "bearer",
            "auth_token": "sk-forbidden",
        },
    )

    assert response.status_code == 403
    data = response.json()
    # RFC 7807 error response
    assert "detail" in data or "title" in data


# ---------------------------------------------------------------------------
# MCP-03: OAuth callback redirect includes workspace slug (Phase 22)
# ---------------------------------------------------------------------------


async def test_oauth_callback_redirect_includes_workspace_slug() -> None:
    """MCP-03: OAuth callback redirect URL includes /{workspace_slug}/settings/mcp-servers.

    When state_data contains workspace_slug, the redirect URL must be
    /{slug}/settings/mcp-servers?status=connected (not /settings/mcp-servers).
    """
    import json
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.api.v1.routers.workspace_mcp_servers import mcp_oauth_callback

    workspace_slug = "my-workspace"
    server_id = uuid4()
    workspace_id = uuid4()
    state = f"mcp_oauth_{server_id}_test-nonce"

    user_id = uuid4()
    state_data = json.dumps(
        {
            "server_id": str(server_id),
            "workspace_id": str(workspace_id),
            "workspace_slug": workspace_slug,
            "user_id": str(user_id),
            "nonce": "test-nonce",
        }
    )

    # Mock Redis client
    mock_redis = MagicMock()
    mock_redis.client = AsyncMock()
    mock_redis.client.get = AsyncMock(return_value=state_data)
    mock_redis.client.delete = AsyncMock()

    # Mock request
    mock_request = MagicMock()
    mock_request.base_url = "http://localhost:8000/"
    mock_request.app.state.container.redis_client.return_value = mock_redis

    # Mock DB session and server
    mock_server = MagicMock()
    mock_server.oauth_token_url = "https://auth.example.com/token"
    mock_server.oauth_client_id = "client-abc"
    mock_server.auth_token_encrypted = None

    mock_repo = AsyncMock()
    mock_repo.get_by_workspace_and_id = AsyncMock(return_value=mock_server)
    mock_repo.update = AsyncMock()

    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "pilot_space.infrastructure.database.get_db_session",
            return_value=mock_session_ctx,
        ),
        patch(
            "pilot_space.infrastructure.database.repositories"
            ".workspace_mcp_server_repository.WorkspaceMcpServerRepository",
            return_value=mock_repo,
        ),
        patch(
            "pilot_space.api.v1.routers.workspace_mcp_servers._exchange_oauth_code",
            return_value="test-access-token",
        ),
        patch(
            "pilot_space.infrastructure.encryption.encrypt_api_key",
            return_value="encrypted-token",
        ),
    ):
        response = await mcp_oauth_callback(
            request=mock_request,
            code="test-code",
            state=state,
        )

    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith(f"/{workspace_slug}/settings/mcp-servers")
    assert "status=connected" in location


async def test_oauth_callback_redirect_fallback_without_slug() -> None:
    """MCP-03: OAuth callback falls back to /settings/mcp-servers without workspace_slug.

    Legacy state_data without workspace_slug key must still produce a valid
    redirect to /settings/mcp-servers (backward compatibility).
    """
    import json
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.api.v1.routers.workspace_mcp_servers import mcp_oauth_callback

    server_id = uuid4()
    workspace_id = uuid4()
    state = f"mcp_oauth_{server_id}_test-nonce"

    user_id = uuid4()
    # Legacy state_data: no workspace_slug key (but user_id is required)
    state_data = json.dumps(
        {
            "server_id": str(server_id),
            "workspace_id": str(workspace_id),
            "user_id": str(user_id),
            "nonce": "test-nonce",
        }
    )

    mock_redis = MagicMock()
    mock_redis.client = AsyncMock()
    mock_redis.client.get = AsyncMock(return_value=state_data)
    mock_redis.client.delete = AsyncMock()

    mock_request = MagicMock()
    mock_request.base_url = "http://localhost:8000/"
    mock_request.app.state.container.redis_client.return_value = mock_redis

    mock_server = MagicMock()
    mock_server.oauth_token_url = "https://auth.example.com/token"
    mock_server.oauth_client_id = "client-abc"
    mock_server.auth_token_encrypted = None

    mock_repo = AsyncMock()
    mock_repo.get_by_workspace_and_id = AsyncMock(return_value=mock_server)
    mock_repo.update = AsyncMock()

    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "pilot_space.infrastructure.database.get_db_session",
            return_value=mock_session_ctx,
        ),
        patch(
            "pilot_space.infrastructure.database.repositories"
            ".workspace_mcp_server_repository.WorkspaceMcpServerRepository",
            return_value=mock_repo,
        ),
        patch(
            "pilot_space.api.v1.routers.workspace_mcp_servers._exchange_oauth_code",
            return_value="test-access-token",
        ),
        patch(
            "pilot_space.infrastructure.encryption.encrypt_api_key",
            return_value="encrypted-token",
        ),
    ):
        response = await mcp_oauth_callback(
            request=mock_request,
            code="test-code",
            state=state,
        )

    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("/settings/mcp-servers")
    assert "status=connected" in location


async def test_oauth_url_stores_workspace_slug_in_state() -> None:
    """MCP-03: get_mcp_oauth_url stores workspace_slug in Redis state_data.

    The OAuth URL generation must include workspace_slug in the state_data
    so the callback can reconstruct the correct redirect URL.
    """
    import json
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.api.v1.routers.workspace_mcp_servers import get_mcp_oauth_url
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
    )

    workspace_id = uuid4()
    server_id = uuid4()

    # Mock workspace with slug
    mock_workspace = MagicMock()
    mock_workspace.slug = "test-workspace"
    mock_workspace.members = [MagicMock(user_id=uuid4(), is_admin=True)]

    # Mock server
    mock_server = MagicMock()
    mock_server.id = server_id
    mock_server.auth_type = McpAuthType.OAUTH2
    mock_server.oauth_auth_url = "https://auth.example.com/authorize"
    mock_server.oauth_client_id = "client-123"
    mock_server.oauth_scopes = "read"

    mock_repo = AsyncMock()
    mock_repo.get_by_workspace_and_id = AsyncMock(return_value=mock_server)

    # Capture what gets stored in Redis
    stored_data: dict[str, object] = {}

    async def capture_set(key: str, value: str, ex: int = 0) -> None:
        stored_data["key"] = key
        stored_data["value"] = json.loads(value)

    mock_redis = MagicMock()
    mock_redis.client = AsyncMock()
    mock_redis.client.set = AsyncMock(side_effect=capture_set)

    mock_request = MagicMock()
    mock_request.base_url = "http://localhost:8000/"
    mock_request.app.state.container.redis_client.return_value = mock_redis

    mock_current_user = MagicMock()
    mock_current_user.user_id = mock_workspace.members[0].user_id

    mock_session = AsyncMock()

    with (
        patch(
            "pilot_space.api.v1.routers.workspace_mcp_servers._get_admin_workspace",
            return_value=mock_workspace,
        ),
        patch(
            "pilot_space.infrastructure.database.repositories"
            ".workspace_mcp_server_repository.WorkspaceMcpServerRepository",
            return_value=mock_repo,
        ),
    ):
        await get_mcp_oauth_url(
            workspace_id=workspace_id,
            server_id=server_id,
            current_user=mock_current_user,
            session=mock_session,
            request=mock_request,
        )

    assert "value" in stored_data
    assert stored_data["value"]["workspace_slug"] == "test-workspace"
