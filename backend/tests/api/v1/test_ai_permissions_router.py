"""Tests for the AI tool permissions router (Phase 69 / 69-05-03).

Uses FastAPI dependency overrides to bypass real auth + DB and exercise
the router -> service contract with a fake PermissionService.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.api.v1.dependencies import _get_permission_service
from pilot_space.application.services.permissions.exceptions import InvalidPolicyError
from pilot_space.application.services.permissions.permission_service import (
    BulkApplyResult,
    ResolvedToolPermission,
)
from pilot_space.dependencies.auth import (
    get_current_user,
    get_session,
    require_workspace_admin,
    require_workspace_member,
)
from pilot_space.domain.permissions.tool_permission_mode import ToolPermissionMode

WORKSPACE_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
CRITICAL_TOOL = "delete_issue"
SAFE_TOOL = "list_notes"


# ---------------------------------------------------------------------------
# Fake service
# ---------------------------------------------------------------------------


@dataclass
class _AuditRow:
    id: UUID
    tool_name: str
    old_mode: str | None
    new_mode: str
    actor_user_id: UUID
    reason: str | None
    created_at: datetime
    workspace_id: UUID


class FakePermissionService:
    """Minimal in-memory fake matching the public PermissionService surface."""

    def __init__(self) -> None:
        self._modes: dict[tuple[UUID, str], ToolPermissionMode] = {}
        self._audit: list[_AuditRow] = []
        self._known = [SAFE_TOOL, CRITICAL_TOOL, "update_note", "create_comment"]
        self._critical = {CRITICAL_TOOL}

    def _default(self, tool_name: str) -> ToolPermissionMode:
        if tool_name in self._critical:
            return ToolPermissionMode.ASK
        return ToolPermissionMode.AUTO if tool_name == SAFE_TOOL else ToolPermissionMode.ASK

    async def list_all(self, workspace_id: UUID) -> list[ResolvedToolPermission]:
        rows: list[ResolvedToolPermission] = []
        for tool in self._known:
            key = (workspace_id, tool)
            if key in self._modes:
                rows.append(
                    ResolvedToolPermission(
                        tool_name=tool,
                        mode=self._modes[key],
                        source="db",
                        can_set_auto=tool not in self._critical,
                    )
                )
            else:
                rows.append(
                    ResolvedToolPermission(
                        tool_name=tool,
                        mode=self._default(tool),
                        source="default",
                        can_set_auto=tool not in self._critical,
                    )
                )
        return rows

    async def set(
        self,
        *,
        workspace_id: UUID,
        tool_name: str,
        mode: ToolPermissionMode,
        actor_user_id: UUID,
        reason: str | None = None,
    ) -> None:
        if tool_name in self._critical and mode is ToolPermissionMode.AUTO:
            raise InvalidPolicyError(
                f"DD-003: tool {tool_name!r} is CRITICAL and cannot be set to 'auto'"
            )
        previous = self._modes.get((workspace_id, tool_name))
        self._modes[(workspace_id, tool_name)] = mode
        self._audit.append(
            _AuditRow(
                id=uuid4(),
                tool_name=tool_name,
                old_mode=previous.value if previous else None,
                new_mode=mode.value,
                actor_user_id=actor_user_id,
                reason=reason,
                created_at=datetime.now(UTC),
                workspace_id=workspace_id,
            )
        )

    async def bulk_apply_template(
        self,
        *,
        workspace_id: UUID,
        template_name: str,
        actor_user_id: UUID,
    ) -> BulkApplyResult:
        if template_name not in ("conservative", "standard", "trusted"):
            raise InvalidPolicyError(f"Unknown template {template_name!r}")
        applied = 0
        skipped: list[str] = []
        for tool in self._known:
            target = (
                ToolPermissionMode.ASK
                if template_name == "conservative"
                else ToolPermissionMode.AUTO
            )
            try:
                await self.set(
                    workspace_id=workspace_id,
                    tool_name=tool,
                    mode=target,
                    actor_user_id=actor_user_id,
                )
                applied += 1
            except InvalidPolicyError:
                skipped.append(tool)
        return BulkApplyResult(template=template_name, applied=applied, skipped=skipped)

    async def list_audit_log(
        self, workspace_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[_AuditRow]:
        rows = [r for r in self._audit if r.workspace_id == workspace_id]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return rows[offset : offset + limit]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_service() -> FakePermissionService:
    return FakePermissionService()


@pytest.fixture
async def admin_client(
    fake_service: FakePermissionService,
) -> AsyncGenerator[AsyncClient, None]:
    from pilot_space.main import app

    async def _noop_session() -> AsyncGenerator[Any, None]:
        yield MagicMock()

    mock_user = MagicMock()
    mock_user.user_id = USER_ID
    mock_user.sub = str(USER_ID)

    app.dependency_overrides[get_session] = _noop_session
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_workspace_admin] = lambda: WORKSPACE_ID
    app.dependency_overrides[require_workspace_member] = lambda: WORKSPACE_ID
    app.dependency_overrides[_get_permission_service] = lambda: fake_service

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test"},
        ) as client:
            yield client
    finally:
        for dep in (
            get_session,
            get_current_user,
            require_workspace_admin,
            require_workspace_member,
            _get_permission_service,
        ):
            app.dependency_overrides.pop(dep, None)


@pytest.fixture
async def member_client(
    fake_service: FakePermissionService,
) -> AsyncGenerator[AsyncClient, None]:
    """Member client: admin dependency raises 403, member passes."""
    from fastapi import HTTPException, status

    from pilot_space.main import app

    async def _noop_session() -> AsyncGenerator[Any, None]:
        yield MagicMock()

    mock_user = MagicMock()
    mock_user.user_id = USER_ID
    mock_user.sub = str(USER_ID)

    def _deny_admin() -> UUID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    app.dependency_overrides[get_session] = _noop_session
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_workspace_member] = lambda: WORKSPACE_ID
    app.dependency_overrides[require_workspace_admin] = _deny_admin
    app.dependency_overrides[_get_permission_service] = lambda: fake_service

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test"},
        ) as client:
            yield client
    finally:
        for dep in (
            get_session,
            get_current_user,
            require_workspace_admin,
            require_workspace_member,
            _get_permission_service,
        ):
            app.dependency_overrides.pop(dep, None)


BASE = f"/api/v1/workspaces/{WORKSPACE_ID}/ai/permissions"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_member_can_list_permissions(member_client: AsyncClient) -> None:
    resp = await member_client.get(BASE)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0
    tool_names = {row["tool_name"] for row in body}
    assert SAFE_TOOL in tool_names
    assert CRITICAL_TOOL in tool_names
    critical_row = next(r for r in body if r["tool_name"] == CRITICAL_TOOL)
    assert critical_row["can_set_auto"] is False


async def test_member_cannot_put_permission(member_client: AsyncClient) -> None:
    resp = await member_client.put(f"{BASE}/{SAFE_TOOL}", json={"mode": "deny"})
    assert resp.status_code == 403


async def test_admin_can_set_and_reflect(admin_client: AsyncClient) -> None:
    resp = await admin_client.put(f"{BASE}/{SAFE_TOOL}", json={"mode": "deny"})
    assert resp.status_code == 200, resp.text
    row = resp.json()
    assert row["tool_name"] == SAFE_TOOL
    assert row["mode"] == "deny"
    assert row["source"] == "db"

    list_resp = await admin_client.get(BASE)
    assert list_resp.status_code == 200
    match = next(r for r in list_resp.json() if r["tool_name"] == SAFE_TOOL)
    assert match["mode"] == "deny"
    assert match["source"] == "db"


async def test_admin_cannot_set_critical_to_auto(admin_client: AsyncClient) -> None:
    resp = await admin_client.put(f"{BASE}/{CRITICAL_TOOL}", json={"mode": "auto"})
    assert resp.status_code == 422, resp.text


async def test_apply_conservative_template(admin_client: AsyncClient) -> None:
    resp = await admin_client.post(f"{BASE}/template/conservative")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["template"] == "conservative"
    assert body["applied"] >= 1

    list_resp = await admin_client.get(BASE)
    rows = list_resp.json()
    # All non-critical tools should be ASK after conservative; critical stays non-AUTO.
    for row in rows:
        if row["tool_name"] != CRITICAL_TOOL:
            assert row["mode"] == "ask"


async def test_audit_log_returns_recent_changes(admin_client: AsyncClient) -> None:
    await admin_client.put(f"{BASE}/{SAFE_TOOL}", json={"mode": "deny"})
    await admin_client.put(f"{BASE}/{SAFE_TOOL}", json={"mode": "ask"})

    resp = await admin_client.get(f"{BASE}/audit-log?limit=10")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) >= 2
    # Most recent first
    assert rows[0]["new_mode"] == "ask"
    assert rows[1]["new_mode"] == "deny"


async def test_audit_log_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.get(f"{BASE}/audit-log")
    assert resp.status_code == 403
