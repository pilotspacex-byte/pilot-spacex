"""Unit tests for PermissionService (Phase 69 — 69-03).

Uses a fake repository + AsyncMock Redis client so tests are hermetic
and do not require a real Postgres (RLS, pgmq, etc.). The service's
``_repo()`` method is monkeypatched to return the fake; the session
ContextVar is never touched.

Covers:
    * resolver fallback chain (LRU -> DB row -> default)
    * LRU hot path < 5ms p95 across 1000 iterations
    * DD-003 invariant: CRITICAL tool cannot be set to AUTO
    * set() writes row + audit log + publishes Redis invalidation
    * bulk_apply_template skips critical/auto violations gracefully
    * list_all() returns all tools with source attribution
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.agents.pilotspace_agent_helpers import ALL_TOOL_NAMES
from pilot_space.ai.sdk.permission_handler import (
    ActionClassification,
    PermissionHandler,
)
from pilot_space.application.services.permissions.exceptions import InvalidPolicyError
from pilot_space.application.services.permissions.permission_cache import (
    INVALIDATION_CHANNEL,
    PermissionCache,
)
from pilot_space.application.services.permissions.permission_service import (
    PermissionService,
)
from pilot_space.domain.permissions.tool_permission_mode import ToolPermissionMode

ACTION_CLASSIFICATIONS = PermissionHandler.ACTION_CLASSIFICATIONS


def _short(tool_name: str) -> str:
    if tool_name.startswith("mcp__"):
        _, _, rest = tool_name.partition("__")
        if "__" in rest:
            return rest.split("__", 1)[1]
    return tool_name


def _classify(tool_name: str) -> ActionClassification | None:
    if tool_name in ACTION_CLASSIFICATIONS:
        return ACTION_CLASSIFICATIONS[tool_name]
    return ACTION_CLASSIFICATIONS.get(_short(tool_name))


# --------------------------------------------------------------------------- #
# Fakes                                                                       #
# --------------------------------------------------------------------------- #


@dataclass
class FakePermissionRow:
    workspace_id: UUID
    tool_name: str
    mode: str
    updated_by: UUID


@dataclass
class FakeAuditRow:
    workspace_id: UUID
    tool_name: str
    old_mode: str | None
    new_mode: str
    actor_user_id: UUID
    reason: str | None


@dataclass
class FakeRepository:
    """In-memory stand-in for ``WorkspaceToolPermissionRepository``."""

    rows: dict[tuple[UUID, str], FakePermissionRow] = field(default_factory=dict)
    audit: list[FakeAuditRow] = field(default_factory=list)

    async def get(self, workspace_id: UUID, tool_name: str) -> FakePermissionRow | None:
        return self.rows.get((workspace_id, tool_name))

    async def list_for_workspace(self, workspace_id: UUID) -> list[FakePermissionRow]:
        return sorted(
            (r for (w, _t), r in self.rows.items() if w == workspace_id),
            key=lambda r: r.tool_name,
        )

    async def upsert(
        self,
        workspace_id: UUID,
        tool_name: str,
        mode: str,
        actor_user_id: UUID,
    ) -> tuple[FakePermissionRow, str | None]:
        key = (workspace_id, tool_name)
        existing = self.rows.get(key)
        if existing is None:
            row = FakePermissionRow(
                workspace_id=workspace_id,
                tool_name=tool_name,
                mode=mode,
                updated_by=actor_user_id,
            )
            self.rows[key] = row
            return row, None
        previous = existing.mode
        existing.mode = mode
        existing.updated_by = actor_user_id
        return existing, previous

    async def insert_audit_log(
        self,
        workspace_id: UUID,
        tool_name: str,
        old_mode: str | None,
        new_mode: str,
        actor_user_id: UUID,
        reason: str | None = None,
    ) -> FakeAuditRow:
        row = FakeAuditRow(
            workspace_id=workspace_id,
            tool_name=tool_name,
            old_mode=old_mode,
            new_mode=new_mode,
            actor_user_id=actor_user_id,
            reason=reason,
        )
        self.audit.append(row)
        return row


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


def _find_critical_tool() -> str:
    for tool in ALL_TOOL_NAMES:
        if _classify(tool) is ActionClassification.CRITICAL_REQUIRE_APPROVAL:
            return tool
    # Fallback to any short CRITICAL key.
    for tool, classification in ACTION_CLASSIFICATIONS.items():
        if classification is ActionClassification.CRITICAL_REQUIRE_APPROVAL:
            return tool
    raise RuntimeError("No CRITICAL tool found — test fixture broken")


def _find_auto_execute_tool() -> str:
    for tool in ALL_TOOL_NAMES:
        if _classify(tool) is ActionClassification.AUTO_EXECUTE:
            return tool
    raise RuntimeError("No AUTO_EXECUTE tool found")


def _find_default_require_tool() -> str:
    for tool in ALL_TOOL_NAMES:
        if _classify(tool) is ActionClassification.DEFAULT_REQUIRE_APPROVAL:
            return tool
    raise RuntimeError("No DEFAULT_REQUIRE_APPROVAL tool found")


@pytest.fixture
def fake_repo() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def fake_redis() -> AsyncMock:
    mock = AsyncMock()
    mock.publish = AsyncMock(return_value=1)
    return mock


@pytest.fixture
def service(
    fake_repo: FakeRepository,
    fake_redis: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> PermissionService:
    svc = PermissionService(
        cache=PermissionCache(),
        redis_client=fake_redis,
    )
    monkeypatch.setattr(svc, "_repo", lambda: fake_repo)
    return svc


@pytest.fixture
def workspace_id() -> UUID:
    return uuid4()


@pytest.fixture
def actor_id() -> UUID:
    return uuid4()


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_resolver_falls_back_to_default_when_no_db_row(
    service: PermissionService, workspace_id: UUID
) -> None:
    tool = _find_auto_execute_tool()
    mode = await service.resolve(workspace_id, tool)
    assert mode is ToolPermissionMode.AUTO

    default_require_tool = _find_default_require_tool()
    mode = await service.resolve(workspace_id, default_require_tool)
    assert mode is ToolPermissionMode.ASK


@pytest.mark.asyncio
async def test_resolver_returns_db_row_when_present(
    service: PermissionService,
    fake_repo: FakeRepository,
    workspace_id: UUID,
    actor_id: UUID,
) -> None:
    tool = _find_auto_execute_tool()  # default=AUTO
    # Force DB row to DENY — resolver must return DENY not AUTO.
    await fake_repo.upsert(workspace_id, tool, "deny", actor_id)
    mode = await service.resolve(workspace_id, tool)
    assert mode is ToolPermissionMode.DENY


@pytest.mark.asyncio
async def test_resolver_uses_lru_cache_under_5ms(
    service: PermissionService, workspace_id: UUID
) -> None:
    tool = _find_auto_execute_tool()
    # Warm the cache.
    await service.resolve(workspace_id, tool)

    samples: list[float] = []
    for _ in range(1000):
        start = time.perf_counter()
        await service.resolve(workspace_id, tool)
        samples.append(time.perf_counter() - start)

    samples.sort()
    p95 = samples[int(len(samples) * 0.95)]
    assert p95 < 0.005, f"p95 {p95 * 1000:.3f}ms exceeds 5ms budget"


@pytest.mark.asyncio
async def test_set_rejects_auto_for_critical_tool(
    service: PermissionService, workspace_id: UUID, actor_id: UUID
) -> None:
    critical = _find_critical_tool()
    with pytest.raises(InvalidPolicyError) as exc_info:
        await service.set(
            workspace_id=workspace_id,
            tool_name=critical,
            mode=ToolPermissionMode.AUTO,
            actor_user_id=actor_id,
        )
    assert exc_info.value.http_status == 422
    assert exc_info.value.error_code == "invalid_permission_policy"


@pytest.mark.asyncio
async def test_set_allows_ask_for_critical_tool(
    service: PermissionService,
    fake_repo: FakeRepository,
    workspace_id: UUID,
    actor_id: UUID,
) -> None:
    critical = _find_critical_tool()
    # ASK is allowed; DENY is allowed; only AUTO is forbidden.
    await service.set(
        workspace_id=workspace_id,
        tool_name=critical,
        mode=ToolPermissionMode.ASK,
        actor_user_id=actor_id,
    )
    assert fake_repo.rows[(workspace_id, critical)].mode == "ask"


@pytest.mark.asyncio
async def test_set_writes_audit_log_row(
    service: PermissionService,
    fake_repo: FakeRepository,
    workspace_id: UUID,
    actor_id: UUID,
) -> None:
    tool = _find_default_require_tool()
    await service.set(
        workspace_id=workspace_id,
        tool_name=tool,
        mode=ToolPermissionMode.DENY,
        actor_user_id=actor_id,
        reason="test reason",
    )
    assert len(fake_repo.audit) == 1
    audit = fake_repo.audit[0]
    assert audit.tool_name == tool
    assert audit.old_mode is None
    assert audit.new_mode == "deny"
    assert audit.actor_user_id == actor_id
    assert audit.reason == "test reason"

    # Second change records the old mode.
    await service.set(
        workspace_id=workspace_id,
        tool_name=tool,
        mode=ToolPermissionMode.ASK,
        actor_user_id=actor_id,
    )
    assert len(fake_repo.audit) == 2
    assert fake_repo.audit[1].old_mode == "deny"
    assert fake_repo.audit[1].new_mode == "ask"


@pytest.mark.asyncio
async def test_set_publishes_redis_invalidation(
    service: PermissionService,
    fake_redis: AsyncMock,
    workspace_id: UUID,
    actor_id: UUID,
) -> None:
    tool = _find_default_require_tool()
    await service.set(
        workspace_id=workspace_id,
        tool_name=tool,
        mode=ToolPermissionMode.DENY,
        actor_user_id=actor_id,
    )
    fake_redis.publish.assert_awaited()
    channel, payload = fake_redis.publish.await_args.args
    assert channel == INVALIDATION_CHANNEL
    assert str(workspace_id) in payload
    assert tool in payload


@pytest.mark.asyncio
async def test_set_invalidates_local_cache(
    service: PermissionService,
    fake_repo: FakeRepository,
    workspace_id: UUID,
    actor_id: UUID,
) -> None:
    tool = _find_auto_execute_tool()  # default AUTO
    # Warm cache to AUTO default.
    assert await service.resolve(workspace_id, tool) is ToolPermissionMode.AUTO
    # Admin downgrades to DENY.
    await service.set(
        workspace_id=workspace_id,
        tool_name=tool,
        mode=ToolPermissionMode.DENY,
        actor_user_id=actor_id,
    )
    # Next resolve must reflect DENY, not cached AUTO.
    assert await service.resolve(workspace_id, tool) is ToolPermissionMode.DENY


@pytest.mark.asyncio
async def test_bulk_apply_template_skips_critical_violations(
    service: PermissionService,
    fake_repo: FakeRepository,
    workspace_id: UUID,
    actor_id: UUID,
) -> None:
    # The "trusted" template already respects DD-003 internally
    # (CRITICAL tools stay ASK). Applying it should skip nothing.
    result = await service.bulk_apply_template(
        workspace_id=workspace_id,
        template_name="trusted",
        actor_user_id=actor_id,
    )
    assert result.template == "trusted"
    assert result.applied > 0
    assert result.skipped == []

    # Verify every CRITICAL tool in the set rows is ASK, not AUTO.
    for (_, tool_name), row in fake_repo.rows.items():
        if _classify(tool_name) is ActionClassification.CRITICAL_REQUIRE_APPROVAL:
            assert row.mode != "auto"


@pytest.mark.asyncio
async def test_bulk_apply_template_unknown_template_raises(
    service: PermissionService, workspace_id: UUID, actor_id: UUID
) -> None:
    with pytest.raises(InvalidPolicyError):
        await service.bulk_apply_template(
            workspace_id=workspace_id,
            template_name="does-not-exist",
            actor_user_id=actor_id,
        )


@pytest.mark.asyncio
async def test_list_returns_all_tools_with_source_attribution(
    service: PermissionService,
    fake_repo: FakeRepository,
    workspace_id: UUID,
    actor_id: UUID,
) -> None:
    # Seed one DB row so we can distinguish 'db' vs 'default'.
    target_tool = _find_default_require_tool()
    await fake_repo.upsert(workspace_id, target_tool, "deny", actor_id)

    rows = await service.list_all(workspace_id)
    assert len(rows) == len(ALL_TOOL_NAMES)

    by_name = {r.tool_name: r for r in rows}
    assert by_name[target_tool].source == "db"
    assert by_name[target_tool].mode is ToolPermissionMode.DENY

    # Sanity: some other tool should resolve to default.
    for tool in ALL_TOOL_NAMES:
        if tool != target_tool:
            assert by_name[tool].source == "default"
            break

    # can_set_auto is False for CRITICAL tools.
    for tool in ALL_TOOL_NAMES:
        if _classify(tool) is ActionClassification.CRITICAL_REQUIRE_APPROVAL:
            assert by_name[tool].can_set_auto is False
        else:
            assert by_name[tool].can_set_auto is True
