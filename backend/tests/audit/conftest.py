"""Shared fixtures for audit log tests.

Provides:
- audit_log_factory: creates AuditLog instances for testing
- audit_client: authenticated AsyncClient with ADMIN role and workspace context
- Reuses db_session, workspace fixtures from parent conftest
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog


@pytest.fixture
def audit_log_factory(db_session: AsyncSession):
    """Factory fixture for creating AuditLog rows.

    Returns a callable that creates and adds an AuditLog to the DB session.
    The caller is responsible for committing the session if needed.

    Usage:
        row = await audit_log_factory(workspace_id=workspace.id, action="issue.create")
    """

    async def _factory(
        *,
        workspace_id: uuid.UUID,
        action: str = "issue.create",
        actor_id: uuid.UUID | None = None,
        actor_type: ActorType = ActorType.USER,
        resource_type: str = "issue",
        resource_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
        ai_input: dict[str, Any] | None = None,
        ai_output: dict[str, Any] | None = None,
        ai_model: str | None = None,
        ai_token_cost: int | None = None,
        ai_rationale: str | None = None,
        ip_address: str | None = "127.0.0.1",
        created_at: datetime | None = None,
    ) -> AuditLog:
        row = AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id or uuid.uuid4(),
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id or uuid.uuid4(),
            payload=payload,
            ai_input=ai_input,
            ai_output=ai_output,
            ai_model=ai_model,
            ai_token_cost=ai_token_cost,
            ai_rationale=ai_rationale,
            ip_address=ip_address,
        )
        if created_at is not None:
            row.created_at = created_at
            row.updated_at = created_at
        db_session.add(row)
        await db_session.flush()
        await db_session.refresh(row)
        return row

    return _factory


_TEST_WORKSPACE_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_TEST_USER_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


def _make_mock_page(items: list | None = None):
    """Create a mock AuditLogPage result."""
    page = MagicMock()
    page.items = items or []
    page.has_next = False
    page.next_cursor = None
    return page


@pytest.fixture
async def audit_client(app: Any) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated AsyncClient with ADMIN workspace context for audit tests.

    Uses FastAPI dependency_overrides to replace auth and session dependencies.
    Patches workspace resolution, RLS context, permission checks, and the
    audit log repository so tests exercise the router without a real DB.

    Args:
        app: FastAPI application fixture from root conftest.

    Yields:
        AsyncClient with Bearer auth header.
    """
    from pilot_space.dependencies.auth import TokenPayload, get_current_user, get_session

    mock_token = TokenPayload(
        sub=str(_TEST_USER_ID),
        email="admin@test.example",
        role="authenticated",
        aud="authenticated",
        exp=9999999999,
        iat=1000000000,
        app_metadata={},
        user_metadata={"full_name": "Test Admin"},
    )

    def _override_current_user() -> TokenPayload:
        return mock_token

    mock_session = AsyncMock(spec=AsyncSession)

    async def _override_get_session():
        yield mock_session

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_session] = _override_get_session

    # Mock the repository to return empty results by default
    mock_repo = MagicMock()
    mock_repo.list_filtered = AsyncMock(return_value=_make_mock_page())
    mock_repo.list_for_export = AsyncMock(return_value=[])

    with (
        patch(
            "pilot_space.api.v1.routers.audit._resolve_workspace",
            new_callable=AsyncMock,
            return_value=_TEST_WORKSPACE_ID,
        ),
        patch(
            "pilot_space.api.v1.routers.audit._require_admin_or_owner",
            new_callable=AsyncMock,
        ),
        patch(
            "pilot_space.api.v1.routers.audit._require_owner",
            new_callable=AsyncMock,
        ),
        patch(
            "pilot_space.api.v1.routers.audit.set_rls_context",
            new_callable=AsyncMock,
        ),
        patch(
            "pilot_space.api.v1.routers.audit.AuditLogRepository",
            return_value=mock_repo,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as ac:
            yield ac

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
async def non_admin_audit_client(app: Any) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated AsyncClient with MEMBER role that fails permission checks.

    Permission helpers raise HTTPException 403 to simulate non-admin access.

    Args:
        app: FastAPI application fixture from root conftest.

    Yields:
        AsyncClient with Bearer auth header but MEMBER-level permissions.
    """
    from fastapi import HTTPException, status

    from pilot_space.dependencies.auth import TokenPayload, get_current_user, get_session

    mock_token = TokenPayload(
        sub=str(_TEST_USER_ID),
        email="member@test.example",
        role="authenticated",
        aud="authenticated",
        exp=9999999999,
        iat=1000000000,
        app_metadata={},
        user_metadata={"full_name": "Test Member"},
    )

    def _override_current_user() -> TokenPayload:
        return mock_token

    mock_session = AsyncMock(spec=AsyncSession)

    async def _override_get_session():
        yield mock_session

    async def _deny_permission(*_args, **_kwargs):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner access required",
        )

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_session] = _override_get_session

    with (
        patch(
            "pilot_space.api.v1.routers.audit._resolve_workspace",
            new_callable=AsyncMock,
            return_value=_TEST_WORKSPACE_ID,
        ),
        patch(
            "pilot_space.api.v1.routers.audit._require_admin_or_owner",
            side_effect=_deny_permission,
        ),
        patch(
            "pilot_space.api.v1.routers.audit._require_owner",
            side_effect=_deny_permission,
        ),
        patch(
            "pilot_space.api.v1.routers.audit.set_rls_context",
            new_callable=AsyncMock,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as ac:
            yield ac

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_session, None)
