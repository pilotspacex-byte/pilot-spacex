"""Tests for the memory router (Phase 69 / 69-05-03 Wave 3).

Covers the recall + lifecycle endpoints (pin, forget, GDPR forget).
Uses FastAPI dependency overrides + fake services to bypass real
auth and DB.
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.api.v1.dependencies import (
    _get_memory_lifecycle_service,
    _get_memory_recall_service,
)
from pilot_space.application.services.memory.memory_lifecycle_service import (
    ForgetPayload,
    GDPRForgetPayload,
    PinPayload,
)
from pilot_space.application.services.memory.memory_recall_service import (
    MemoryItem,
    RecallPayload,
    RecallResult,
)
from pilot_space.dependencies.auth import (
    get_current_user,
    get_session,
    require_workspace_admin,
    require_workspace_member,
)

WORKSPACE_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
MEMORY_ID = UUID("33333333-3333-3333-3333-333333333333")
TARGET_USER_ID = UUID("44444444-4444-4444-4444-444444444444")


# ---------------------------------------------------------------------------
# Fake services
# ---------------------------------------------------------------------------


class FakeRecallService:
    def __init__(self) -> None:
        self.calls: list[RecallPayload] = []

    async def recall(self, payload: RecallPayload) -> RecallResult:
        self.calls.append(payload)
        return RecallResult(
            items=[
                MemoryItem(
                    source_type="note",
                    source_id="note-1",
                    node_id=str(uuid4()),
                    score=0.91,
                    snippet="hello world",
                    created_at="2026-04-07T00:00:00+00:00",
                )
            ],
            cache_hit=False,
            elapsed_ms=12.5,
        )


class FakeLifecycleService:
    def __init__(self) -> None:
        self.pin_calls: list[PinPayload] = []
        self.forget_calls: list[ForgetPayload] = []
        self.gdpr_calls: list[GDPRForgetPayload] = []

    async def pin(self, payload: PinPayload) -> None:
        self.pin_calls.append(payload)

    async def forget(self, payload: ForgetPayload) -> None:
        self.forget_calls.append(payload)

    async def gdpr_forget_user(self, payload: GDPRForgetPayload) -> int:
        self.gdpr_calls.append(payload)
        return 3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_recall() -> FakeRecallService:
    return FakeRecallService()


@pytest.fixture
def fake_lifecycle() -> FakeLifecycleService:
    return FakeLifecycleService()


def _mock_user() -> Any:
    user = MagicMock()
    user.user_id = USER_ID
    user.sub = str(USER_ID)
    return user


async def _noop_session() -> AsyncGenerator[Any, None]:
    yield MagicMock()


@pytest.fixture
async def admin_client(
    fake_recall: FakeRecallService,
    fake_lifecycle: FakeLifecycleService,
) -> AsyncGenerator[AsyncClient, None]:
    from pilot_space.main import app

    app.dependency_overrides[get_session] = _noop_session
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[require_workspace_admin] = lambda: WORKSPACE_ID
    app.dependency_overrides[require_workspace_member] = lambda: WORKSPACE_ID
    app.dependency_overrides[_get_memory_recall_service] = lambda: fake_recall
    app.dependency_overrides[_get_memory_lifecycle_service] = lambda: fake_lifecycle

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
            _get_memory_recall_service,
            _get_memory_lifecycle_service,
        ):
            app.dependency_overrides.pop(dep, None)


@pytest.fixture
async def member_client(
    fake_recall: FakeRecallService,
    fake_lifecycle: FakeLifecycleService,
) -> AsyncGenerator[AsyncClient, None]:
    from fastapi import HTTPException, status

    from pilot_space.main import app

    def _deny_admin() -> UUID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    app.dependency_overrides[get_session] = _noop_session
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[require_workspace_member] = lambda: WORKSPACE_ID
    app.dependency_overrides[require_workspace_admin] = _deny_admin
    app.dependency_overrides[_get_memory_recall_service] = lambda: fake_recall
    app.dependency_overrides[_get_memory_lifecycle_service] = lambda: fake_lifecycle

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
            _get_memory_recall_service,
            _get_memory_lifecycle_service,
        ):
            app.dependency_overrides.pop(dep, None)


BASE = f"/api/v1/workspaces/{WORKSPACE_ID}/ai/memory"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_member_can_recall(
    member_client: AsyncClient, fake_recall: FakeRecallService
) -> None:
    resp = await member_client.post(
        f"{BASE}/recall",
        json={"query": "auth flow", "k": 5, "min_score": 0.5},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    assert body["cacheHit"] is False
    assert isinstance(body["elapsedMs"], int)
    assert len(body["items"]) == 1
    assert body["items"][0]["score"] == pytest.approx(0.91)
    # Service was called with the right payload
    assert len(fake_recall.calls) == 1
    assert fake_recall.calls[0].query == "auth flow"
    assert fake_recall.calls[0].k == 5
    assert fake_recall.calls[0].workspace_id == WORKSPACE_ID


async def test_recall_rejects_empty_query(member_client: AsyncClient) -> None:
    resp = await member_client.post(f"{BASE}/recall", json={"query": ""})
    assert resp.status_code == 422


async def test_member_cannot_pin(member_client: AsyncClient) -> None:
    resp = await member_client.post(f"{BASE}/{MEMORY_ID}/pin")
    assert resp.status_code == 403


async def test_admin_can_pin(
    admin_client: AsyncClient, fake_lifecycle: FakeLifecycleService
) -> None:
    resp = await admin_client.post(f"{BASE}/{MEMORY_ID}/pin")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"success": True}
    assert len(fake_lifecycle.pin_calls) == 1
    assert fake_lifecycle.pin_calls[0].node_id == MEMORY_ID
    assert fake_lifecycle.pin_calls[0].workspace_id == WORKSPACE_ID
    assert fake_lifecycle.pin_calls[0].actor_user_id == USER_ID


async def test_member_cannot_forget(member_client: AsyncClient) -> None:
    resp = await member_client.delete(f"{BASE}/{MEMORY_ID}")
    assert resp.status_code == 403


async def test_admin_can_forget(
    admin_client: AsyncClient, fake_lifecycle: FakeLifecycleService
) -> None:
    resp = await admin_client.delete(f"{BASE}/{MEMORY_ID}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"success": True}
    assert len(fake_lifecycle.forget_calls) == 1
    assert fake_lifecycle.forget_calls[0].node_id == MEMORY_ID


async def test_member_cannot_gdpr_forget(member_client: AsyncClient) -> None:
    resp = await member_client.post(
        f"{BASE}/gdpr-forget-user",
        json={"user_id": str(TARGET_USER_ID)},
    )
    assert resp.status_code == 403


async def test_admin_can_gdpr_forget(
    admin_client: AsyncClient, fake_lifecycle: FakeLifecycleService
) -> None:
    resp = await admin_client.post(
        f"{BASE}/gdpr-forget-user",
        json={"user_id": str(TARGET_USER_ID)},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"success": True}
    assert len(fake_lifecycle.gdpr_calls) == 1
    assert fake_lifecycle.gdpr_calls[0].user_id == TARGET_USER_ID


def test_routes_use_empty_string_on_collection_roots() -> None:
    """Guard against accidental ``/`` collection roots that cause 307 redirects."""
    from pilot_space.api.v1.routers import memory as memory_module

    src = inspect.getsource(memory_module)
    # No bare "/" route decorators in this router
    assert '@router.post("/")' not in src
    assert '@router.get("/")' not in src
    assert '@router.delete("/")' not in src
