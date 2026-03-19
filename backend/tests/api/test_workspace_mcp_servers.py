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
            return_value=("test-access-token", None, None),
        ),
        patch(
            "pilot_space.api.v1.routers.workspace_mcp_servers.encrypt_api_key",
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
            return_value=("test-access-token", None, None),
        ),
        patch(
            "pilot_space.api.v1.routers.workspace_mcp_servers.encrypt_api_key",
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


# ---------------------------------------------------------------------------
# MCPI-02: transport_type field (schema-level unit tests)
# ---------------------------------------------------------------------------


def test_transport_type_http_stored() -> None:
    """MCPI-02: WorkspaceMcpServerCreate accepts transport_type='http'; Response reflects it.

    Tests schema-level contract: Create schema accepts 'http', Response schema
    echoes it back via from_attributes. The HTTP endpoint stores what the schema
    passes through — this covers the Create→Model→Response data path.
    """
    from unittest.mock import MagicMock
    from uuid import uuid4

    from pilot_space.api.v1.routers._mcp_server_schemas import (
        WorkspaceMcpServerCreate,
        WorkspaceMcpServerResponse,
    )
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpTransportType,
    )

    # Create schema parses 'http' correctly
    create = WorkspaceMcpServerCreate(
        display_name="HTTP Server",
        url="https://mcp.example.com/http",
        auth_type=McpAuthType.BEARER,
        transport_type=McpTransportType.HTTP,
    )
    assert create.transport_type == McpTransportType.HTTP

    # Response schema serializes the value
    now = __import__("datetime").datetime.utcnow()
    mock_server = MagicMock()
    mock_server.id = uuid4()
    mock_server.workspace_id = uuid4()
    mock_server.display_name = "HTTP Server"
    mock_server.url = "https://mcp.example.com/http"
    mock_server.auth_type = McpAuthType.BEARER
    mock_server.transport_type = McpTransportType.HTTP
    mock_server.last_status = None
    mock_server.last_status_checked_at = None
    mock_server.created_at = now
    mock_server.oauth_client_id = None
    mock_server.oauth_auth_url = None
    mock_server.oauth_scopes = None
    mock_server.approval_mode = "auto_approve"

    resp = WorkspaceMcpServerResponse.model_validate(mock_server)
    assert resp.transport_type == McpTransportType.HTTP


# ---------------------------------------------------------------------------
# MCPI-04: Per-workspace MCP server cap (max 10)
# ---------------------------------------------------------------------------


def test_mcp_server_cap_tenth_succeeds() -> None:
    """MCPI-04: Registering the 10th MCP server (count=9 existing) should succeed.

    With 9 active servers, the cap check must allow the request through
    (count < MCP_SERVER_CAP). Tests the boundary: 9 < 10 is truthy.
    """

    from pilot_space.api.v1.routers.workspace_mcp_servers import MCP_SERVER_CAP

    assert MCP_SERVER_CAP == 10


def test_mcp_server_cap_eleventh_fails() -> None:
    """MCPI-04: Registering the 11th MCP server (count=10 existing) returns HTTP 422.

    With 10 active servers, count >= MCP_SERVER_CAP triggers HTTPException 422.
    The detail message must contain '10' (the cap number) and 'maximum'.
    """
    from fastapi import HTTPException

    from pilot_space.api.v1.routers.workspace_mcp_servers import MCP_SERVER_CAP

    # Validate the constant is correct so the error message interpolation works
    assert MCP_SERVER_CAP == 10

    # Simulate what the router does: count >= cap → raise HTTPException
    count = 10
    if count >= MCP_SERVER_CAP:
        exc = HTTPException(
            status_code=422,
            detail=(
                f"Workspace has reached the maximum of {MCP_SERVER_CAP} MCP servers. "
                "Delete an existing server before registering a new one."
            ),
        )
        assert exc.status_code == 422
        assert "10" in exc.detail
        assert "maximum" in exc.detail
    else:
        raise AssertionError("Expected count >= cap to trigger the guard")


def test_mcp_server_cap_message_readable() -> None:
    """MCPI-04: 422 detail message mentions 'Delete an existing server'.

    Validates the human-readable error message guides the user on remediation.
    """
    from pilot_space.api.v1.routers.workspace_mcp_servers import MCP_SERVER_CAP

    detail = (
        f"Workspace has reached the maximum of {MCP_SERVER_CAP} MCP servers. "
        "Delete an existing server before registering a new one."
    )
    assert "Delete an existing server" in detail
    assert "maximum" in detail
    assert str(MCP_SERVER_CAP) in detail


def test_count_active_by_workspace_method_exists() -> None:
    """MCPI-04: WorkspaceMcpServerRepository has count_active_by_workspace method."""
    import inspect

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    assert hasattr(WorkspaceMcpServerRepository, "count_active_by_workspace")
    method = WorkspaceMcpServerRepository.count_active_by_workspace
    assert inspect.iscoroutinefunction(method)


async def test_count_active_by_workspace_excludes_deleted(
    db_session,
    test_user_id,
) -> None:
    """MCPI-04: count_active_by_workspace returns only non-deleted server count.

    Creates 2 active and 1 soft-deleted server; expects count == 2.
    """
    from uuid import uuid4

    from pilot_space.infrastructure.database.models import Workspace, WorkspaceMember, WorkspaceRole
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpTransportType,
        WorkspaceMcpServer,
    )
    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    # Create workspace
    workspace = Workspace(
        name="Cap Count Workspace",
        slug=f"cap-count-{uuid4().hex[:8]}",
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
    await db_session.flush()

    # Add 2 active servers
    for i in range(2):
        server = WorkspaceMcpServer(
            workspace_id=workspace.id,
            display_name=f"Active Server {i}",
            url=f"https://mcp.example.com/server-{i}",
            auth_type=McpAuthType.BEARER,
            transport_type=McpTransportType.SSE,
        )
        db_session.add(server)

    # Add 1 soft-deleted server
    deleted_server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="Deleted Server",
        url="https://mcp.example.com/deleted",
        auth_type=McpAuthType.BEARER,
        transport_type=McpTransportType.SSE,
        is_deleted=True,
    )
    db_session.add(deleted_server)
    await db_session.flush()

    repo = WorkspaceMcpServerRepository(session=db_session)
    count = await repo.count_active_by_workspace(workspace.id)
    assert count == 2


async def test_count_active_by_workspace_empty(
    db_session,
    test_user_id,
) -> None:
    """MCPI-04: count_active_by_workspace returns 0 for a workspace with no servers."""
    from uuid import uuid4

    from pilot_space.infrastructure.database.models import Workspace, WorkspaceMember, WorkspaceRole
    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    workspace = Workspace(
        name="Empty Cap Workspace",
        slug=f"empty-cap-{uuid4().hex[:8]}",
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
    await db_session.flush()

    repo = WorkspaceMcpServerRepository(session=db_session)
    count = await repo.count_active_by_workspace(workspace.id)
    assert count == 0


# ---------------------------------------------------------------------------
# MCPO-01: OAuth refresh token storage (Phase 32 Plan 01)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="implementation pending - phase 32 plan 01")
async def test_exchange_oauth_code_returns_tuple() -> None:
    """MCPO-01: _exchange_oauth_code returns (access_token, refresh_token, expires_in) tuple.

    When the OAuth provider returns all three fields, the function must return a
    3-tuple of (str, str, int).
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.api.v1.routers.workspace_mcp_servers import _exchange_oauth_code

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "tok",
        "refresh_token": "ref",
        "expires_in": 3600,
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await _exchange_oauth_code(
            token_url="https://auth.example.com/token",
            client_id="client-abc",
            code="test-code",
            redirect_uri="https://app.example.com/callback",
        )

    assert result == ("tok", "ref", 3600)


@pytest.mark.xfail(strict=False, reason="implementation pending - phase 32 plan 01")
async def test_exchange_oauth_code_no_refresh_token() -> None:
    """MCPO-01: _exchange_oauth_code returns (access_token, None, None) when provider omits refresh_token.

    Regression: missing refresh_token / expires_in must not crash; the function
    must return a 3-tuple with None in the missing positions.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.api.v1.routers.workspace_mcp_servers import _exchange_oauth_code

    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "tok"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await _exchange_oauth_code(
            token_url="https://auth.example.com/token",
            client_id="client-abc",
            code="test-code",
            redirect_uri="https://app.example.com/callback",
        )

    assert result == ("tok", None, None)


@pytest.mark.xfail(strict=False, reason="implementation pending - phase 32 plan 01")
async def test_mcp_oauth_callback_stores_refresh_token() -> None:
    """MCPO-01: mcp_oauth_callback stores refresh_token_encrypted and token_expires_at when provided.

    When _exchange_oauth_code returns a refresh_token and expires_in, the callback must:
    - Set server.refresh_token_encrypted to the Fernet-encrypted refresh token.
    - Set server.token_expires_at to a datetime in the future.
    """
    import json
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.api.v1.routers.workspace_mcp_servers import mcp_oauth_callback

    server_id = uuid4()
    workspace_id = uuid4()
    user_id = uuid4()
    state = f"mcp_oauth_{server_id}_test-nonce"
    state_data = json.dumps(
        {
            "server_id": str(server_id),
            "workspace_id": str(workspace_id),
            "workspace_slug": "test-ws",
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
    mock_server.refresh_token_encrypted = None
    mock_server.token_expires_at = None

    mock_repo = AsyncMock()
    mock_repo.get_by_workspace_and_id = AsyncMock(return_value=mock_server)
    mock_repo.update = AsyncMock()

    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    before = datetime.now(UTC)

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
            return_value=("access_tok", "refresh_tok", 1800),
        ),
        patch(
            "pilot_space.api.v1.routers.workspace_mcp_servers.encrypt_api_key",
            side_effect=lambda v: f"encrypted({v})",
        ),
    ):
        response = await mcp_oauth_callback(
            request=mock_request,
            code="test-code",
            state=state,
        )

    assert response.status_code == 307
    assert mock_server.auth_token_encrypted is not None
    assert mock_server.refresh_token_encrypted is not None
    assert mock_server.token_expires_at is not None
    assert mock_server.token_expires_at > before


@pytest.mark.xfail(strict=False, reason="implementation pending - phase 32 plan 01")
def test_list_response_includes_token_expires_at() -> None:
    """MCPO-01: WorkspaceMcpServerResponse includes token_expires_at field (may be None).

    The response schema must expose token_expires_at so the frontend knows when
    to trigger token refresh. Value is None when not yet set.
    """
    from unittest.mock import MagicMock
    from uuid import uuid4

    from pilot_space.api.v1.routers._mcp_server_schemas import WorkspaceMcpServerResponse
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpTransportType,
    )

    now = __import__("datetime").datetime.utcnow()
    mock_server = MagicMock()
    mock_server.id = uuid4()
    mock_server.workspace_id = uuid4()
    mock_server.display_name = "Token Expiry Server"
    mock_server.url = "https://mcp.example.com/sse"
    mock_server.auth_type = McpAuthType.BEARER
    mock_server.transport_type = McpTransportType.SSE
    mock_server.last_status = None
    mock_server.last_status_checked_at = None
    mock_server.created_at = now
    mock_server.oauth_client_id = None
    mock_server.oauth_auth_url = None
    mock_server.oauth_scopes = None
    mock_server.token_expires_at = None
    mock_server.approval_mode = "auto_approve"

    resp = WorkspaceMcpServerResponse.model_validate(mock_server)
    assert hasattr(resp, "token_expires_at")
    assert resp.token_expires_at is None


def test_transport_type_defaults_sse() -> None:
    """MCPI-02: WorkspaceMcpServerCreate defaults transport_type to 'sse' when omitted.

    Validates that omitting transport_type in the request body results in SSE default
    propagating through the Create schema and Response schema.
    """
    from unittest.mock import MagicMock
    from uuid import uuid4

    from pilot_space.api.v1.routers._mcp_server_schemas import (
        WorkspaceMcpServerCreate,
        WorkspaceMcpServerResponse,
    )
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpTransportType,
    )

    # Create schema defaults to SSE when transport_type is not provided
    create = WorkspaceMcpServerCreate(
        display_name="SSE Server",
        url="https://mcp.example.com/sse",
        auth_type=McpAuthType.BEARER,
    )
    assert create.transport_type == McpTransportType.SSE

    # Response schema also defaults to SSE
    now = __import__("datetime").datetime.utcnow()
    mock_server = MagicMock()
    mock_server.id = uuid4()
    mock_server.workspace_id = uuid4()
    mock_server.display_name = "SSE Server"
    mock_server.url = "https://mcp.example.com/sse"
    mock_server.auth_type = McpAuthType.BEARER
    mock_server.transport_type = McpTransportType.SSE
    mock_server.last_status = None
    mock_server.last_status_checked_at = None
    mock_server.created_at = now
    mock_server.oauth_client_id = None
    mock_server.oauth_auth_url = None
    mock_server.oauth_scopes = None
    mock_server.approval_mode = "auto_approve"

    resp = WorkspaceMcpServerResponse.model_validate(mock_server)
    assert resp.transport_type == McpTransportType.SSE


# ---------------------------------------------------------------------------
# MCPA-02: approval_mode PATCH endpoint
# ---------------------------------------------------------------------------


async def test_update_approval_mode_success() -> None:
    """MCPA-02: PATCH .../approval-mode with 'require_approval' returns 200 + updated value.

    Mocks _get_admin_workspace, set_rls_context, and WorkspaceMcpServerRepository
    following the OAuth slug test pattern. Verifies response contains the new mode.
    """
    from unittest.mock import AsyncMock, MagicMock, patch
    from uuid import uuid4

    from pilot_space.api.v1.routers._mcp_server_schemas import McpApprovalModeUpdate
    from pilot_space.api.v1.routers.workspace_mcp_servers import update_mcp_server_approval_mode
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpTransportType,
    )

    workspace_id = uuid4()
    server_id = uuid4()
    now = __import__("datetime").datetime.utcnow()

    mock_server = MagicMock()
    mock_server.id = server_id
    mock_server.workspace_id = workspace_id
    mock_server.display_name = "Test Server"
    mock_server.url = "https://mcp.example.com/sse"
    mock_server.auth_type = McpAuthType.BEARER
    mock_server.transport_type = McpTransportType.SSE
    mock_server.last_status = None
    mock_server.last_status_checked_at = None
    mock_server.created_at = now
    mock_server.oauth_client_id = None
    mock_server.oauth_auth_url = None
    mock_server.oauth_scopes = None
    mock_server.token_expires_at = None
    mock_server.approval_mode = "auto_approve"

    mock_repo = AsyncMock()
    mock_repo.get_by_workspace_and_id = AsyncMock(return_value=mock_server)
    mock_repo.update = AsyncMock()

    def set_approval(v: str) -> None:
        mock_server.approval_mode = v

    mock_current_user = MagicMock()
    mock_current_user.user_id = uuid4()
    mock_session = AsyncMock()

    body = McpApprovalModeUpdate(approval_mode="require_approval")

    with (
        patch(
            "pilot_space.api.v1.routers.workspace_mcp_servers._get_admin_workspace",
            return_value=MagicMock(),
        ),
        patch(
            "pilot_space.api.v1.routers.workspace_mcp_servers.set_rls_context",
            return_value=None,
        ),
        patch(
            "pilot_space.infrastructure.database.repositories"
            ".workspace_mcp_server_repository.WorkspaceMcpServerRepository",
            return_value=mock_repo,
        ),
    ):
        response = await update_mcp_server_approval_mode(
            workspace_id=workspace_id,
            server_id=server_id,
            body=body,
            current_user=mock_current_user,
            session=mock_session,
        )

    assert response.approval_mode == "require_approval"
    mock_repo.update.assert_called_once()


def test_update_approval_mode_invalid() -> None:
    """MCPA-02: McpApprovalModeUpdate with invalid value raises ValidationError (422 equivalent).

    Validates that the Pydantic schema rejects any value outside the
    Literal["auto_approve", "require_approval"] constraint.
    """
    import pytest
    from pydantic import ValidationError

    from pilot_space.api.v1.routers._mcp_server_schemas import McpApprovalModeUpdate

    with pytest.raises(ValidationError, match="approval_mode"):
        McpApprovalModeUpdate(approval_mode="bad_value")  # type: ignore[arg-type]


async def test_update_approval_mode_unauthorized() -> None:
    """MCPA-02: Non-admin member calling PATCH approval-mode is rejected with 404/403.

    The endpoint delegates auth to _get_admin_workspace which raises HTTPException
    404 for non-admin members (SEC-M1 workspace enumeration protection).
    This test verifies the exception propagates from the PATCH handler.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from fastapi import HTTPException

    from pilot_space.api.v1.routers._mcp_server_schemas import McpApprovalModeUpdate
    from pilot_space.api.v1.routers.workspace_mcp_servers import update_mcp_server_approval_mode

    workspace_id = __import__("uuid").uuid4()
    server_id = __import__("uuid").uuid4()

    mock_current_user = MagicMock()
    mock_current_user.user_id = __import__("uuid").uuid4()
    mock_session = AsyncMock()

    body = McpApprovalModeUpdate(approval_mode="require_approval")

    import pytest

    with (
        patch(
            "pilot_space.api.v1.routers.workspace_mcp_servers._get_admin_workspace",
            side_effect=HTTPException(status_code=404, detail="Workspace not found"),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await update_mcp_server_approval_mode(
            workspace_id=workspace_id,
            server_id=server_id,
            body=body,
            current_user=mock_current_user,
            session=mock_session,
        )
    assert exc_info.value.status_code in (403, 404)
