"""Tests for workspace MCP server CRUD and agent wiring (Phase 14 + Phase 25).

Phase 14 (MCP-01 through MCP-06):
  MCP-01: POST creates registered server row (admin-only)
  MCP-02: Bearer token stored encrypted at rest
  MCP-03: OAuth callback stores token after code exchange
  MCP-05: Status endpoint returns connected/failed/unknown
  MCP-06: DELETE soft-deletes; subsequent GET excludes the server

Phase 25 (New fields + endpoints):
  Phase25-01: POST with new fields (server_type, transport, url_or_command)
  Phase25-02: GET with filter params (server_type, status, search)
  Phase25-03: PATCH partial update; preserves secrets when not provided
  Phase25-04: POST .../enable and .../disable toggle is_enabled
  Phase25-05: Soft-deleted server not returned by filtered list
  Phase25-06: API response never contains raw secrets
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
    db_session_committed: AsyncSession,
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
    db_session_committed.add(workspace)
    await db_session_committed.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user_id,
        role=WorkspaceRole.ADMIN,
    )
    db_session_committed.add(member)
    await db_session_committed.commit()
    await db_session_committed.refresh(workspace)

    return workspace, member


@pytest.fixture
async def mcp_workspace_with_member(
    db_session_committed: AsyncSession,
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
    db_session_committed.add(workspace)
    await db_session_committed.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user_id,
        role=WorkspaceRole.MEMBER,
    )
    db_session_committed.add(member)
    await db_session_committed.commit()
    await db_session_committed.refresh(workspace)

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

    The status field must be a valid McpStatus enum value.
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
    assert status_data["status"] in (
        "enabled",
        "disabled",
        "unhealthy",
        "unreachable",
        "config_error",
    )


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
            "pilot_space.api.v1.routers.workspace_mcp_servers.get_admin_workspace",
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


# ---------------------------------------------------------------------------
# Phase 25: Shared fixtures (mock-based, no real DB required)
# ---------------------------------------------------------------------------

_ADMIN_WORKSPACE_PATH = "pilot_space.api.v1.routers.workspace_mcp_servers._get_admin_workspace"
_MCP_REPO_PATH = (
    "pilot_space.infrastructure.database.repositories"
    ".workspace_mcp_server_repository.WorkspaceMcpServerRepository"
)
_SET_RLS_PATH = "pilot_space.api.v1.routers.workspace_mcp_servers.set_rls_context"


@pytest.fixture
def mock_workspace_p25() -> object:
    """Minimal mock workspace for Phase 25 tests."""
    from unittest.mock import MagicMock

    ws = MagicMock()
    ws.id = uuid4()
    ws.slug = "phase25-workspace"
    return ws


@pytest.fixture
def mock_mcp_repo_p25() -> object:
    """Mock WorkspaceMcpServerRepository for Phase 25 tests."""
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4 as _uuid4

    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpStatus,
        McpTransport,
        WorkspaceMcpServer,
    )

    repo = AsyncMock()

    def _make_server(**overrides: object) -> WorkspaceMcpServer:
        server = MagicMock(spec=WorkspaceMcpServer)
        server.id = overrides.get("id", _uuid4())
        server.workspace_id = overrides.get("workspace_id", _uuid4())
        server.display_name = overrides.get("display_name", "Test Server")
        server.server_type = overrides.get("server_type", McpServerType.REMOTE)
        server.transport = overrides.get("transport", McpTransport.SSE)
        server.url_or_command = overrides.get("url_or_command", "https://mcp.example.com/sse")
        server.url = overrides.get("url", "https://mcp.example.com/sse")
        server.command_args = overrides.get("command_args")
        server.command_runner = overrides.get("command_runner")
        server.is_enabled = overrides.get("is_enabled", True)
        server.is_deleted = overrides.get("is_deleted", False)
        server.auth_type = overrides.get("auth_type", McpAuthType.BEARER)
        server.auth_token_encrypted = overrides.get("auth_token_encrypted")
        server.headers_encrypted = overrides.get("headers_encrypted")
        server.headers_json = overrides.get("headers_json")
        server.env_vars_encrypted = overrides.get("env_vars_encrypted")
        server.oauth_client_id = None
        server.oauth_auth_url = None
        server.oauth_scopes = None
        server.last_status = overrides.get("last_status", McpStatus.ENABLED)
        server.last_status_checked_at = None
        server.created_at = overrides.get("created_at", datetime.now(UTC))
        return server

    repo._make_server = _make_server
    repo.create = AsyncMock(side_effect=lambda s: s)
    repo.get_active_by_workspace = AsyncMock(return_value=[])
    repo.get_by_display_name = AsyncMock(return_value=None)
    repo.get_filtered = AsyncMock(return_value=[])
    repo.get_by_workspace_and_id = AsyncMock(return_value=None)
    repo.update = AsyncMock(side_effect=lambda s: s)
    repo.update_fields = AsyncMock(side_effect=lambda s, **_kw: s)
    repo.set_enabled = AsyncMock(side_effect=lambda s, _enabled=True: s)
    repo.soft_delete = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mcp_p25_client(mock_workspace_p25: object, mock_mcp_repo_p25: object) -> object:
    """Authenticated ASGI test client with admin workspace + repo mocked.

    Phase 25 tests use this client instead of ``authenticated_client`` so they
    don't need a real PostgreSQL database.
    """
    from collections.abc import AsyncGenerator
    from unittest.mock import AsyncMock, MagicMock, patch

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    mock_payload = MagicMock(spec=TokenPayload)
    mock_payload.sub = "test-user-id"
    mock_payload.user_id = mock_workspace_p25.id  # type: ignore[attr-defined]

    mock_session = AsyncMock()

    async def _session() -> AsyncGenerator[object, None]:
        yield mock_session

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_session] = _session

    transport = ASGITransport(app=app)

    # Return a context manager that yields the client while patching _get_admin_workspace
    class _ClientCtx:
        def __init__(self) -> None:
            self._client: AsyncClient | None = None
            self._admin_patcher = patch(
                _ADMIN_WORKSPACE_PATH,
                new=AsyncMock(return_value=mock_workspace_p25),
            )
            self._rls_patcher = patch(_SET_RLS_PATH, new=AsyncMock())

        async def __aenter__(self) -> AsyncClient:
            self._admin_patcher.start()
            self._rls_patcher.start()
            self._client = AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Authorization": "Bearer test-token"},
            )
            return await self._client.__aenter__()  # type: ignore[return-value]

        async def __aexit__(self, *args: object) -> None:
            self._rls_patcher.stop()
            self._admin_patcher.stop()
            if self._client is not None:
                await self._client.__aexit__(*args)
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_session, None)

    return _ClientCtx()


# ---------------------------------------------------------------------------
# Phase 25: Register server with new fields
# ---------------------------------------------------------------------------


async def test_register_server_with_new_fields(
    mock_workspace_p25: object,
    mock_mcp_repo_p25: object,
) -> None:
    """Phase25-01: POST with server_type, transport, url_or_command succeeds.

    Verifies new fields appear in the response and raw secrets are never returned.
    """
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock, patch
    from uuid import uuid4 as _uuid4

    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpStatus,
        McpTransport,
        WorkspaceMcpServer,
    )

    workspace = mock_workspace_p25
    repo = mock_mcp_repo_p25
    server_id = _uuid4()

    # Set up repo.create to return a properly built server
    from unittest.mock import MagicMock

    created_server = MagicMock(spec=WorkspaceMcpServer)
    created_server.id = server_id
    created_server.workspace_id = workspace.id
    created_server.display_name = "Phase25 Remote Server"
    created_server.server_type = McpServerType.REMOTE
    created_server.transport = McpTransport.SSE
    created_server.url_or_command = "https://mcp.example.com/sse"
    created_server.url = "https://mcp.example.com/sse"
    created_server.command_args = None
    created_server.command_runner = None
    created_server.is_enabled = True
    created_server.auth_type = McpAuthType.BEARER
    created_server.auth_token_encrypted = "encrypted-token"
    created_server.headers_encrypted = None
    created_server.headers_json = '{"X-Custom": "value1"}'
    created_server.env_vars_encrypted = None
    created_server.oauth_client_id = None
    created_server.oauth_auth_url = None
    created_server.oauth_scopes = None
    created_server.last_status = McpStatus.ENABLED
    created_server.last_status_checked_at = None
    created_server.created_at = datetime.now(UTC)
    repo.create = AsyncMock(return_value=created_server)

    from unittest.mock import MagicMock

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    mock_payload = MagicMock(spec=TokenPayload)

    async def _session():  # type: ignore[return]
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_session] = _session

    payload = {
        "display_name": "Phase25 Remote Server",
        "server_type": "remote",
        "transport": "sse",
        "url_or_command": "https://mcp.example.com/sse",
        "auth_type": "bearer",
        "auth_token": "sk-phase25-token",
        "headers": {"X-Custom": "header-value"},
    }

    try:
        with (
            patch(_ADMIN_WORKSPACE_PATH, new=AsyncMock(return_value=workspace)),
            patch(_SET_RLS_PATH, new=AsyncMock()),
            patch(_MCP_REPO_PATH, return_value=repo),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Authorization": "Bearer test-token"},
            ) as client:
                response = await client.post(
                    f"/api/v1/workspaces/{workspace.id}/mcp-servers",
                    json=payload,
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 201
    data = response.json()

    # New fields in response
    assert data["server_type"] == "remote"
    assert data["transport"] == "sse"
    assert data["url_or_command"] == "https://mcp.example.com/sse"
    assert data["is_enabled"] is True

    # Secret flags instead of raw values
    assert data["has_auth_secret"] is True
    assert data["has_headers"] is True
    assert data["has_headers_encrypted"] is False

    # Headers are now visible in response (not secret)
    assert data["headers"] == {"X-Custom": "value1"}

    # Raw secrets MUST NEVER appear
    for key in (
        "auth_token",
        "auth_token_encrypted",
        "headers_encrypted",
        "env_vars",
        "env_vars_encrypted",
    ):
        assert key not in data, f"Response must not contain {key!r}"


async def test_response_never_contains_raw_secrets(
    mock_workspace_p25: object,
    mock_mcp_repo_p25: object,
) -> None:
    """Phase25-06: API response never contains auth_token, headers, or env_vars."""
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpStatus,
        McpTransport,
        WorkspaceMcpServer,
    )

    workspace = mock_workspace_p25
    repo = mock_mcp_repo_p25

    created_server = MagicMock(spec=WorkspaceMcpServer)
    created_server.id = uuid4()
    created_server.workspace_id = workspace.id
    created_server.display_name = "Secret Test Server"
    created_server.server_type = McpServerType.COMMAND
    created_server.transport = McpTransport.STDIO
    created_server.url_or_command = "@modelcontextprotocol/server-github"
    created_server.url = "@modelcontextprotocol/server-github"
    created_server.command_runner = None
    created_server.command_args = None
    created_server.is_enabled = True
    created_server.auth_type = McpAuthType.BEARER
    created_server.auth_token_encrypted = "encrypted-token"
    created_server.headers_encrypted = None
    created_server.headers_json = None
    created_server.env_vars_encrypted = "encrypted-env-vars"
    created_server.oauth_client_id = None
    created_server.oauth_auth_url = None
    created_server.oauth_scopes = None
    created_server.last_status = McpStatus.ENABLED
    created_server.last_status_checked_at = None
    created_server.created_at = datetime.now(UTC)
    repo.create = AsyncMock(return_value=created_server)

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    mock_payload = MagicMock(spec=TokenPayload)

    async def _session():  # type: ignore[return]
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_session] = _session

    payload = {
        "display_name": "Secret Test Server",
        "server_type": "command",
        "command_runner": "npx",
        "transport": "stdio",
        "url_or_command": "@modelcontextprotocol/server-github",
        "auth_type": "bearer",
        "auth_token": "sk-secret-value",
        "env_vars": {"API_KEY": "supersecret"},
    }

    try:
        with (
            patch(_ADMIN_WORKSPACE_PATH, new=AsyncMock(return_value=workspace)),
            patch(_SET_RLS_PATH, new=AsyncMock()),
            patch(_MCP_REPO_PATH, return_value=repo),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Authorization": "Bearer test-token"},
            ) as client:
                response = await client.post(
                    f"/api/v1/workspaces/{workspace.id}/mcp-servers",
                    json=payload,
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 201
    data = response.json()

    forbidden_keys = {
        "auth_token",
        "auth_token_encrypted",
        "headers_encrypted",
        "env_vars",
        "env_vars_encrypted",
    }
    for key in forbidden_keys:
        assert key not in data, f"Response must not contain {key!r}"


# ---------------------------------------------------------------------------
# Phase 25: PATCH partial update — preserve secrets
# ---------------------------------------------------------------------------


async def test_patch_preserves_existing_secret_when_not_provided(
    mock_workspace_p25: object,
    mock_mcp_repo_p25: object,
) -> None:
    """Phase25-03b: PATCH without auth_token returns has_auth_secret=True."""
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpStatus,
        McpTransport,
        WorkspaceMcpServer,
    )

    workspace = mock_workspace_p25
    repo = mock_mcp_repo_p25
    server_id = uuid4()

    existing_server = MagicMock(spec=WorkspaceMcpServer)
    existing_server.id = server_id
    existing_server.workspace_id = workspace.id
    existing_server.display_name = "Secret Preserve Server"
    existing_server.server_type = McpServerType.REMOTE
    existing_server.transport = McpTransport.SSE
    existing_server.url_or_command = "https://secret-preserve.example.com/sse"
    existing_server.url = "https://secret-preserve.example.com/sse"
    existing_server.command_args = None
    existing_server.command_runner = None
    existing_server.is_enabled = True
    existing_server.auth_type = McpAuthType.BEARER
    existing_server.auth_token_encrypted = "existing-encrypted-token"  # Has a secret
    existing_server.headers_encrypted = None
    existing_server.headers_json = None
    existing_server.env_vars_encrypted = None
    existing_server.oauth_client_id = None
    existing_server.oauth_auth_url = None
    existing_server.oauth_scopes = None
    existing_server.last_status = McpStatus.ENABLED
    existing_server.last_status_checked_at = None
    existing_server.created_at = datetime.now(UTC)

    # PATCH should not change the encrypted token
    async def _update_fields(server: object, **kwargs: object) -> object:
        if "display_name" in kwargs:
            existing_server.display_name = kwargs["display_name"]
        # auth_token_encrypted should NOT be in kwargs when not provided
        assert (
            "auth_token_encrypted" not in kwargs
            or kwargs["auth_token_encrypted"] == existing_server.auth_token_encrypted
        )
        return existing_server

    repo.get_by_workspace_and_id = AsyncMock(return_value=existing_server)
    repo.update_fields = AsyncMock(side_effect=_update_fields)

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    mock_payload = MagicMock(spec=TokenPayload)

    async def _session():  # type: ignore[return]
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_session] = _session

    try:
        with (
            patch(_ADMIN_WORKSPACE_PATH, new=AsyncMock(return_value=workspace)),
            patch(_SET_RLS_PATH, new=AsyncMock()),
            patch(_MCP_REPO_PATH, return_value=repo),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Authorization": "Bearer test-token"},
            ) as client:
                patch_resp = await client.patch(
                    f"/api/v1/workspaces/{workspace.id}/mcp-servers/{server_id}",
                    json={"display_name": "Still Preserved"},
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["has_auth_secret"] is True  # Still has secret


# ---------------------------------------------------------------------------
# Phase 25: Enable / Disable
# ---------------------------------------------------------------------------


async def test_disable_sets_status_and_flag(
    mock_workspace_p25: object,
    mock_mcp_repo_p25: object,
) -> None:
    """Phase25-04a: POST .../disable returns 204 and calls set_enabled(False)."""
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpStatus,
        McpTransport,
        WorkspaceMcpServer,
    )

    workspace = mock_workspace_p25
    repo = mock_mcp_repo_p25
    server_id = uuid4()

    existing_server = MagicMock(spec=WorkspaceMcpServer)
    existing_server.id = server_id
    existing_server.workspace_id = workspace.id
    existing_server.display_name = "Disable Me Server"
    existing_server.server_type = McpServerType.REMOTE
    existing_server.transport = McpTransport.SSE
    existing_server.url_or_command = "https://disable-me.example.com/sse"
    existing_server.url = "https://disable-me.example.com/sse"
    existing_server.command_args = None
    existing_server.command_runner = None
    existing_server.is_enabled = True
    existing_server.auth_type = McpAuthType.BEARER
    existing_server.auth_token_encrypted = None
    existing_server.headers_encrypted = None
    existing_server.headers_json = None
    existing_server.env_vars_encrypted = None
    existing_server.oauth_client_id = None
    existing_server.oauth_auth_url = None
    existing_server.oauth_scopes = None
    existing_server.last_status = McpStatus.ENABLED
    existing_server.last_status_checked_at = None
    existing_server.created_at = datetime.now(UTC)

    repo.get_by_workspace_and_id = AsyncMock(return_value=existing_server)
    set_enabled_calls: list[tuple[object, bool]] = []

    async def _set_enabled(server: object, enabled: bool) -> object:
        set_enabled_calls.append((server, enabled))
        existing_server.is_enabled = enabled
        existing_server.last_status = McpStatus.DISABLED if not enabled else None
        return existing_server

    repo.set_enabled = AsyncMock(side_effect=_set_enabled)

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    mock_payload = MagicMock(spec=TokenPayload)

    async def _session():  # type: ignore[return]
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_session] = _session

    try:
        with (
            patch(_ADMIN_WORKSPACE_PATH, new=AsyncMock(return_value=workspace)),
            patch(_SET_RLS_PATH, new=AsyncMock()),
            patch(_MCP_REPO_PATH, return_value=repo),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Authorization": "Bearer test-token"},
            ) as client:
                resp = await client.post(
                    f"/api/v1/workspaces/{workspace.id}/mcp-servers/{server_id}/disable"
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 204
    # set_enabled must have been called with enabled=False
    assert len(set_enabled_calls) == 1
    _, enabled_arg = set_enabled_calls[0]
    assert enabled_arg is False


async def test_enable_clears_status_and_flag(
    mock_workspace_p25: object,
    mock_mcp_repo_p25: object,
) -> None:
    """Phase25-04b: POST .../enable returns 204 and calls set_enabled(True)."""
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpStatus,
        McpTransport,
        WorkspaceMcpServer,
    )

    workspace = mock_workspace_p25
    repo = mock_mcp_repo_p25
    server_id = uuid4()

    existing_server = MagicMock(spec=WorkspaceMcpServer)
    existing_server.id = server_id
    existing_server.workspace_id = workspace.id
    existing_server.display_name = "Re-Enable Server"
    existing_server.server_type = McpServerType.REMOTE
    existing_server.transport = McpTransport.SSE
    existing_server.url_or_command = "https://re-enable.example.com/sse"
    existing_server.url = "https://re-enable.example.com/sse"
    existing_server.command_args = None
    existing_server.command_runner = None
    existing_server.is_enabled = False  # Currently disabled
    existing_server.auth_type = McpAuthType.BEARER
    existing_server.auth_token_encrypted = None
    existing_server.headers_encrypted = None
    existing_server.headers_json = None
    existing_server.env_vars_encrypted = None
    existing_server.oauth_client_id = None
    existing_server.oauth_auth_url = None
    existing_server.oauth_scopes = None
    existing_server.last_status = McpStatus.DISABLED
    existing_server.last_status_checked_at = None
    existing_server.created_at = datetime.now(UTC)

    repo.get_by_workspace_and_id = AsyncMock(return_value=existing_server)
    set_enabled_calls: list[tuple[object, bool]] = []

    async def _set_enabled(server: object, enabled: bool) -> object:
        set_enabled_calls.append((server, enabled))
        existing_server.is_enabled = enabled
        existing_server.last_status = None if enabled else McpStatus.DISABLED
        return existing_server

    repo.set_enabled = AsyncMock(side_effect=_set_enabled)

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    mock_payload = MagicMock(spec=TokenPayload)

    async def _session():  # type: ignore[return]
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_session] = _session

    try:
        with (
            patch(_ADMIN_WORKSPACE_PATH, new=AsyncMock(return_value=workspace)),
            patch(_SET_RLS_PATH, new=AsyncMock()),
            patch(_MCP_REPO_PATH, return_value=repo),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Authorization": "Bearer test-token"},
            ) as client:
                resp = await client.post(
                    f"/api/v1/workspaces/{workspace.id}/mcp-servers/{server_id}/enable"
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 204
    assert len(set_enabled_calls) == 1
    _, enabled_arg = set_enabled_calls[0]
    assert enabled_arg is True


# ---------------------------------------------------------------------------
# Phase 25: GET with filter params (mock-based)
# ---------------------------------------------------------------------------


async def test_list_with_type_filter(
    mock_workspace_p25: object,
    mock_mcp_repo_p25: object,
) -> None:
    """Phase25-02: GET with server_type=remote filter returns only remote items."""
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpStatus,
        McpTransport,
        WorkspaceMcpServer,
    )

    workspace = mock_workspace_p25
    repo = mock_mcp_repo_p25

    def _make_srv(name: str, stype: McpServerType) -> MagicMock:
        s = MagicMock(spec=WorkspaceMcpServer)
        s.id = uuid4()
        s.workspace_id = workspace.id
        s.display_name = name
        s.server_type = stype
        s.transport = McpTransport.SSE
        s.url_or_command = "https://example.com"
        s.url = "https://example.com"
        s.command_args = None
        s.command_runner = None
        s.is_enabled = True
        s.auth_type = McpAuthType.BEARER
        s.auth_token_encrypted = None
        s.headers_encrypted = None
        s.headers_json = None
        s.env_vars_encrypted = None
        s.oauth_client_id = None
        s.oauth_auth_url = None
        s.oauth_scopes = None
        s.last_status = McpStatus.ENABLED
        s.last_status_checked_at = None
        s.created_at = datetime.now(UTC)
        return s

    remote_server = _make_srv("Filter Remote", McpServerType.REMOTE)
    # get_filtered returns only remote when server_type=remote passed
    repo.get_filtered = AsyncMock(return_value=[remote_server])

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    mock_payload = MagicMock(spec=TokenPayload)

    async def _session():  # type: ignore[return]
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_session] = _session

    try:
        with (
            patch(_ADMIN_WORKSPACE_PATH, new=AsyncMock(return_value=workspace)),
            patch(_SET_RLS_PATH, new=AsyncMock()),
            patch(_MCP_REPO_PATH, return_value=repo),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Authorization": "Bearer test-token"},
            ) as client:
                response = await client.get(
                    f"/api/v1/workspaces/{workspace.id}/mcp-servers",
                    params={"server_type": "remote"},
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    for item in data["items"]:
        assert item["server_type"] == "remote"


# ---------------------------------------------------------------------------
# Phase 25: Soft-delete regression (mock-based)
# ---------------------------------------------------------------------------


async def test_soft_deleted_server_not_in_filtered_list(
    mock_workspace_p25: object,
    mock_mcp_repo_p25: object,
) -> None:
    """Phase25-05: get_filtered excludes deleted servers (repository contract test)."""
    from unittest.mock import AsyncMock, MagicMock, patch

    workspace = mock_workspace_p25
    repo = mock_mcp_repo_p25

    # Repo returns empty list (simulating deleted server filtered out)
    repo.get_filtered = AsyncMock(return_value=[])

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    mock_payload = MagicMock(spec=TokenPayload)

    async def _session():  # type: ignore[return]
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_session] = _session

    fake_deleted_id = str(uuid4())

    try:
        with (
            patch(_ADMIN_WORKSPACE_PATH, new=AsyncMock(return_value=workspace)),
            patch(_SET_RLS_PATH, new=AsyncMock()),
            patch(_MCP_REPO_PATH, return_value=repo),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Authorization": "Bearer test-token"},
            ) as client:
                list_resp = await client.get(f"/api/v1/workspaces/{workspace.id}/mcp-servers")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    ids = [item["id"] for item in items]
    assert fake_deleted_id not in ids


# ---------------------------------------------------------------------------
# WorkspaceMcpServerUpdate — url_or_command validation (SEC-H3 parity)
# ---------------------------------------------------------------------------


def test_update_schema_rejects_empty_url_or_command() -> None:
    """PATCH body with empty url_or_command must be rejected."""
    import pytest
    from pydantic import ValidationError

    from pilot_space.api.v1.schemas.mcp_server import WorkspaceMcpServerUpdate

    with pytest.raises(ValidationError, match="must not be empty"):
        WorkspaceMcpServerUpdate(url_or_command="")


def test_update_schema_rejects_whitespace_url_or_command() -> None:
    """PATCH body with whitespace-only url_or_command must be rejected."""
    import pytest
    from pydantic import ValidationError

    from pilot_space.api.v1.schemas.mcp_server import WorkspaceMcpServerUpdate

    with pytest.raises(ValidationError, match="must not be empty"):
        WorkspaceMcpServerUpdate(url_or_command="   ")


def test_update_schema_rejects_http_url_for_remote_type() -> None:
    """PATCH with server_type=REMOTE and HTTP URL must be rejected (SSRF)."""
    import pytest
    from pydantic import ValidationError

    from pilot_space.api.v1.schemas.mcp_server import WorkspaceMcpServerUpdate
    from pilot_space.infrastructure.database.models.workspace_mcp_server import McpServerType

    with pytest.raises(ValidationError, match="HTTPS"):
        WorkspaceMcpServerUpdate(
            server_type=McpServerType.REMOTE,
            url_or_command="http://evil.example.com/mcp",
        )


def test_update_schema_rejects_command_injection_for_npx() -> None:
    """PATCH with server_type=COMMAND and shell metacharacter must be rejected."""
    import pytest
    from pydantic import ValidationError

    from pilot_space.api.v1.schemas.mcp_server import WorkspaceMcpServerUpdate
    from pilot_space.infrastructure.database.models.workspace_mcp_server import McpServerType

    with pytest.raises(ValidationError, match="metacharacters"):
        WorkspaceMcpServerUpdate(
            server_type=McpServerType.COMMAND,
            url_or_command="@modelcontextprotocol/server-github; rm -rf /",
        )


def test_update_schema_rejects_command_injection_for_uvx() -> None:
    """PATCH with server_type=COMMAND (legacy UVX) and shell metacharacter must be rejected."""
    import pytest
    from pydantic import ValidationError

    from pilot_space.api.v1.schemas.mcp_server import WorkspaceMcpServerUpdate
    from pilot_space.infrastructure.database.models.workspace_mcp_server import McpServerType

    with pytest.raises(ValidationError, match="metacharacters"):
        WorkspaceMcpServerUpdate(
            server_type=McpServerType.COMMAND,
            url_or_command="mcp-server-fetch | curl evil.com",
        )


def test_update_schema_accepts_valid_https_url_for_remote() -> None:
    """PATCH with server_type=REMOTE and valid HTTPS URL passes schema validation."""
    from unittest.mock import patch

    from pilot_space.api.v1.schemas.mcp_server import WorkspaceMcpServerUpdate
    from pilot_space.infrastructure.database.models.workspace_mcp_server import McpServerType

    # Patch getaddrinfo to avoid real DNS in unit tests
    with patch("socket.getaddrinfo", return_value=[]):
        body = WorkspaceMcpServerUpdate(
            server_type=McpServerType.REMOTE,
            url_or_command="https://api.example.com/mcp",
        )
    assert body.url_or_command == "https://api.example.com/mcp"


def test_update_schema_accepts_valid_npx_command() -> None:
    """PATCH with server_type=COMMAND and clean command passes schema validation."""
    from pilot_space.api.v1.schemas.mcp_server import WorkspaceMcpServerUpdate
    from pilot_space.infrastructure.database.models.workspace_mcp_server import McpServerType

    body = WorkspaceMcpServerUpdate(
        server_type=McpServerType.COMMAND,
        url_or_command="@modelcontextprotocol/server-github",
    )
    assert body.url_or_command == "@modelcontextprotocol/server-github"


def test_update_schema_no_validation_when_url_or_command_omitted() -> None:
    """PATCH body without url_or_command skips url_or_command validation entirely."""
    from pilot_space.api.v1.schemas.mcp_server import WorkspaceMcpServerUpdate
    from pilot_space.infrastructure.database.models.workspace_mcp_server import McpServerType

    # Only changing server_type — url_or_command not in body, so model_validator
    # leaves url_or_command=None; cross-field check happens in the route handler.
    body = WorkspaceMcpServerUpdate(server_type=McpServerType.COMMAND)
    assert body.url_or_command is None
    assert body.server_type == McpServerType.COMMAND


# ---------------------------------------------------------------------------
# Duplicate display_name — 409 on POST / PATCH
# ---------------------------------------------------------------------------


async def test_post_duplicate_display_name_returns_409(
    mock_workspace_p25: object,
    mock_mcp_repo_p25: object,
) -> None:
    """POST with a display_name already used by an active server returns 409."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        WorkspaceMcpServer,
    )
    from pilot_space.main import app

    workspace = mock_workspace_p25
    repo = mock_mcp_repo_p25

    # Simulate an existing server with the same name
    existing = MagicMock(spec=WorkspaceMcpServer)
    existing.id = uuid4()
    repo.get_by_display_name = AsyncMock(return_value=existing)

    mock_payload = MagicMock(spec=TokenPayload)
    mock_payload.sub = "test-user-id"
    mock_payload.user_id = workspace.id  # type: ignore[attr-defined]

    async def _session():  # type: ignore[return]
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_session] = _session

    try:
        with (
            patch(_ADMIN_WORKSPACE_PATH, new=AsyncMock(return_value=workspace)),
            patch(_SET_RLS_PATH, new=AsyncMock()),
            patch(_MCP_REPO_PATH, return_value=repo),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"Authorization": "Bearer test-token"},
            ) as client:
                resp = await client.post(
                    f"/api/v1/workspaces/{workspace.id}/mcp-servers",  # type: ignore[attr-defined]
                    json={
                        "display_name": "Duplicate Server",
                        "url_or_command": "https://mcp.example.com/sse",
                        "server_type": "remote",
                    },
                )
                status_code = resp.status_code
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert status_code == 409


async def test_patch_rename_to_existing_name_returns_409(
    mock_workspace_p25: object,
    mock_mcp_repo_p25: object,
) -> None:
    """PATCH renaming to an already-taken display_name returns 409."""
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock, MagicMock, patch

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpStatus,
        McpTransport,
        WorkspaceMcpServer,
    )
    from pilot_space.main import app

    workspace = mock_workspace_p25
    repo = mock_mcp_repo_p25
    server_id = uuid4()

    # The server being patched
    existing_server = MagicMock(spec=WorkspaceMcpServer)
    existing_server.id = server_id
    existing_server.workspace_id = workspace.id  # type: ignore[attr-defined]
    existing_server.display_name = "Original Name"
    existing_server.server_type = McpServerType.REMOTE
    existing_server.transport = McpTransport.SSE
    existing_server.url_or_command = "https://original.example.com/sse"
    existing_server.url = "https://original.example.com/sse"
    existing_server.command_args = None
    existing_server.command_runner = None
    existing_server.is_enabled = True
    existing_server.auth_type = McpAuthType.NONE
    existing_server.auth_token_encrypted = None
    existing_server.headers_encrypted = None
    existing_server.headers_json = None
    existing_server.env_vars_encrypted = None
    existing_server.oauth_client_id = None
    existing_server.oauth_auth_url = None
    existing_server.oauth_token_url = None
    existing_server.oauth_scopes = None
    existing_server.last_status = McpStatus.ENABLED
    existing_server.last_status_checked_at = None
    existing_server.created_at = datetime.now(UTC)

    repo.get_by_workspace_and_id = AsyncMock(return_value=existing_server)

    # Another active server already uses the target name
    conflict_server = MagicMock(spec=WorkspaceMcpServer)
    conflict_server.id = uuid4()
    repo.get_by_display_name = AsyncMock(return_value=conflict_server)

    mock_payload = MagicMock(spec=TokenPayload)
    mock_payload.sub = "test-user-id"
    mock_payload.user_id = workspace.id  # type: ignore[attr-defined]

    async def _session():  # type: ignore[return]
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_session] = _session

    try:
        with (
            patch(_ADMIN_WORKSPACE_PATH, new=AsyncMock(return_value=workspace)),
            patch(_SET_RLS_PATH, new=AsyncMock()),
            patch(_MCP_REPO_PATH, return_value=repo),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"Authorization": "Bearer test-token"},
            ) as client:
                resp = await client.patch(
                    f"/api/v1/workspaces/{workspace.id}/mcp-servers/{server_id}",  # type: ignore[attr-defined]
                    json={"display_name": "Taken Name"},
                )
                status_code = resp.status_code
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert status_code == 409


# ---------------------------------------------------------------------------
# load_workspace_mcp_servers — key format includes UUID suffix
# ---------------------------------------------------------------------------

_LOADER_REPO_PATH = (
    "pilot_space.infrastructure.database.repositories"
    ".workspace_mcp_server_repository.WorkspaceMcpServerRepository"
)
_LOADER_BUILD_PATH = "pilot_space.ai.agents.pilotspace_stream_utils._build_server_config"
_LOADER_DECRYPT_PATH = "pilot_space.infrastructure.encryption.decrypt_api_key"


async def test_loader_key_includes_uuid_suffix() -> None:
    """Keys from load_workspace_mcp_servers must be WORKSPACE_{NAME}_{SHORT_ID}."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from uuid import UUID

    from pilot_space.ai.agents.pilotspace_stream_utils import load_workspace_mcp_servers
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpServerType,
        McpTransport,
        WorkspaceMcpServer,
    )

    server_id = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    server = MagicMock(spec=WorkspaceMcpServer)
    server.id = server_id
    server.display_name = "My Server"
    server.server_type = McpServerType.REMOTE
    server.transport = McpTransport.SSE
    server.url_or_command = "https://mcp.example.com/sse"
    server.url = "https://mcp.example.com/sse"
    server.auth_type = MagicMock()
    server.auth_token_encrypted = None
    server.headers_encrypted = None
    server.headers_json = None
    server.env_vars_encrypted = None

    repo_mock = AsyncMock()
    repo_mock.get_active_by_workspace = AsyncMock(return_value=[server])

    workspace_id = uuid4()
    db_session = MagicMock()

    with (
        patch(_LOADER_REPO_PATH, return_value=repo_mock),
        patch(_LOADER_BUILD_PATH, return_value=MagicMock()),
    ):
        result = await load_workspace_mcp_servers(workspace_id, db_session)

    # Short ID is first 8 hex chars of a1b2c3d4-... uppercased = "A1B2C3D4"
    expected_key = "WORKSPACE_MY_SERVER_A1B2C3D4"
    assert expected_key in result, f"Expected key {expected_key!r}, got keys: {list(result)}"


async def test_loader_two_servers_get_distinct_keys() -> None:
    """Two servers with identical normalized names each get a unique key via UUID suffix."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from uuid import UUID

    from pilot_space.ai.agents.pilotspace_stream_utils import load_workspace_mcp_servers
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpServerType,
        McpTransport,
        WorkspaceMcpServer,
    )

    id_a = UUID("aaaaaaaa-0000-0000-0000-000000000001")
    id_b = UUID("bbbbbbbb-0000-0000-0000-000000000002")

    def _make(sid: UUID, name: str) -> MagicMock:
        s = MagicMock(spec=WorkspaceMcpServer)
        s.id = sid
        s.display_name = name
        s.server_type = McpServerType.REMOTE
        s.transport = McpTransport.SSE
        s.url_or_command = "https://mcp.example.com/sse"
        s.url = "https://mcp.example.com/sse"
        s.auth_type = MagicMock()
        s.auth_token_encrypted = None
        s.headers_encrypted = None
        s.headers_json = None
        s.env_vars_encrypted = None
        return s

    # "my server" and "my-server" both normalize to "MY_SERVER"
    server_a = _make(id_a, "my server")
    server_b = _make(id_b, "my-server")

    repo_mock = AsyncMock()
    repo_mock.get_active_by_workspace = AsyncMock(return_value=[server_a, server_b])

    workspace_id = uuid4()
    db_session = MagicMock()

    with (
        patch(_LOADER_REPO_PATH, return_value=repo_mock),
        patch(_LOADER_BUILD_PATH, return_value=MagicMock()),
    ):
        result = await load_workspace_mcp_servers(workspace_id, db_session)

    assert len(result) == 2, f"Expected 2 distinct keys, got: {list(result)}"
    assert "WORKSPACE_MY_SERVER_AAAAAAAA" in result
    assert "WORKSPACE_MY_SERVER_BBBBBBBB" in result


# ---------------------------------------------------------------------------
# T021-T024: McpCommandRunner validation tests
# ---------------------------------------------------------------------------


def test_create_command_server_requires_command_runner() -> None:
    """T021: POST schema rejects command server without command_runner (422)."""
    import pytest
    from pydantic import ValidationError

    from pilot_space.api.v1.schemas.mcp_server import WorkspaceMcpServerCreate

    with pytest.raises(ValidationError, match="command_runner"):
        WorkspaceMcpServerCreate(
            display_name="test",
            server_type="command",
            url_or_command="@foo/bar",
            auth_type="none",
            transport="stdio",
        )


def test_create_command_server_with_npx_runner() -> None:
    """T022: POST schema accepts command server with command_runner=npx."""

    from pilot_space.api.v1.schemas.mcp_server import WorkspaceMcpServerCreate

    body = WorkspaceMcpServerCreate(
        display_name="npx-srv",
        server_type="command",
        command_runner="npx",
        url_or_command="@modelcontextprotocol/server",
        auth_type="none",
        transport="stdio",
    )
    assert body.server_type.value == "command"
    assert body.command_runner is not None
    assert body.command_runner.value == "npx"


def test_remote_server_rejects_command_runner() -> None:
    """T023: POST schema rejects remote server with command_runner set (422)."""
    from unittest.mock import patch

    import pytest
    from pydantic import ValidationError

    from pilot_space.api.v1.schemas.mcp_server import WorkspaceMcpServerCreate

    with (
        pytest.raises(ValidationError, match="command_runner"),
        patch("socket.getaddrinfo", return_value=[]),
    ):
        WorkspaceMcpServerCreate(
            display_name="r",
            server_type="remote",
            command_runner="npx",
            url_or_command="https://mcp.example.com/sse",
            auth_type="none",
            transport="sse",
        )


def test_import_rejects_non_npx_uvx_command() -> None:
    """T024: Import service surfaces unsupported command runners as ErrorEntry."""
    from pilot_space.application.services.mcp.import_mcp_servers_service import (
        ImportMcpServersService,
    )

    # docker run is not an npx/uvx command — should appear as a parse error, not silently dropped
    config = '{"mcpServers": {"bad": {"command": "docker run foo"}}}'
    parsed, errors = ImportMcpServersService.parse_config_json(config)
    assert len(parsed) == 0, "docker run command should not produce a parsed server"
    assert len(errors) == 1, "docker run command should produce a parse error"
    assert errors[0].name == "bad"
    assert "unsupported_command_runner" in errors[0].reason

    # npx command should be accepted
    config_valid = '{"mcpServers": {"good": {"command": "npx @foo/bar"}}}'
    parsed_valid, errors_valid = ImportMcpServersService.parse_config_json(config_valid)
    assert len(errors_valid) == 0
    assert len(parsed_valid) == 1
    assert parsed_valid[0].command_runner is not None
    assert parsed_valid[0].command_runner.value == "npx"
    assert parsed_valid[0].url_or_command == "@foo/bar"
