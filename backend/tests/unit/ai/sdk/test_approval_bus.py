"""Tests for UnifiedApprovalBus module.

Covers:
- UnifiedApprovalBus: register/wait/resolve cycle, claim-once semantics, timeout, cleanup
- get_approval_bus(): module-level singleton
- SSE helpers: classify_urgency, build_affected_entities, build_approval_sse_event
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch
from uuid import uuid4

import pytest

from pilot_space.ai.sdk.approval_bus import (
    ApprovalActionExecutor,
    UnifiedApprovalBus,
    build_affected_entities,
    build_approval_sse_event,
    classify_urgency,
    get_approval_bus,
)

# ---------------------------------------------------------------------------
# TestUnifiedApprovalBus
# ---------------------------------------------------------------------------


class TestUnifiedApprovalBus:
    """Tests for UnifiedApprovalBus register/wait/resolve cycle."""

    @pytest.mark.asyncio
    async def test_register_resolve_wait_cycle(self) -> None:
        """Test 1: register(id) + resolve(id, 'approved') -> resolve returns True, wait returns 'approved'."""
        bus = UnifiedApprovalBus()
        approval_id = uuid4()

        bus.register(approval_id)
        result = bus.resolve(approval_id, "approved")
        assert result is True

        decision = await bus.wait(approval_id, timeout_seconds=1.0)
        assert decision == "approved"

    @pytest.mark.asyncio
    async def test_resolve_unknown_id_returns_false(self) -> None:
        """Test 2: resolve(unknown_id, 'approved') -> returns False."""
        bus = UnifiedApprovalBus()
        result = bus.resolve(uuid4(), "approved")
        assert result is False

    @pytest.mark.asyncio
    async def test_claim_once_second_resolve_returns_false(self) -> None:
        """Test 3: register + resolve + resolve -> second resolve returns False (claim-once, APPR-02)."""
        bus = UnifiedApprovalBus()
        approval_id = uuid4()

        bus.register(approval_id)
        first = bus.resolve(approval_id, "approved")
        second = bus.resolve(approval_id, "rejected")

        assert first is True
        assert second is False

    @pytest.mark.asyncio
    async def test_wait_timeout_returns_expired(self) -> None:
        """Test 4: register(id) + wait(id, timeout=0.01) -> returns 'expired' (timeout)."""
        bus = UnifiedApprovalBus()
        approval_id = uuid4()

        bus.register(approval_id)
        decision = await bus.wait(approval_id, timeout_seconds=0.01)
        assert decision == "expired"

    @pytest.mark.asyncio
    async def test_wait_cleans_up_pending(self) -> None:
        """Test 5: register + resolve + wait -> cleans up _pending (no memory leak)."""
        bus = UnifiedApprovalBus()
        approval_id = uuid4()

        bus.register(approval_id)
        bus.resolve(approval_id, "approved")
        await bus.wait(approval_id, timeout_seconds=1.0)

        # _pending should be empty after wait completes
        assert approval_id not in bus._pending

    @pytest.mark.asyncio
    async def test_wait_unregistered_returns_expired(self) -> None:
        """Test 6: wait(unregistered_id) -> returns 'expired'."""
        bus = UnifiedApprovalBus()
        decision = await bus.wait(uuid4(), timeout_seconds=1.0)
        assert decision == "expired"

    @pytest.mark.asyncio
    async def test_concurrent_register_resolve(self) -> None:
        """Test 7: concurrent register + resolve from different coroutines -> resolves correctly."""
        bus = UnifiedApprovalBus()
        approval_id = uuid4()

        bus.register(approval_id)

        async def resolver():
            await asyncio.sleep(0.01)
            bus.resolve(approval_id, "approved")

        # Start resolver and waiter concurrently
        task = asyncio.create_task(resolver())
        decision = await bus.wait(approval_id, timeout_seconds=5.0)
        await task

        assert decision == "approved"


# ---------------------------------------------------------------------------
# TestGetApprovalBus
# ---------------------------------------------------------------------------


class TestGetApprovalBus:
    """Test get_approval_bus() singleton."""

    def test_singleton_returns_same_instance(self) -> None:
        """Test 8: get_approval_bus() returns singleton instance."""
        # Reset module-level singleton for test isolation
        import pilot_space.ai.sdk.approval_bus as bus_module

        bus_module._bus = None

        bus1 = get_approval_bus()
        bus2 = get_approval_bus()
        assert bus1 is bus2
        assert isinstance(bus1, UnifiedApprovalBus)

        # Clean up
        bus_module._bus = None


# ---------------------------------------------------------------------------
# TestClassifyUrgency
# ---------------------------------------------------------------------------


class TestClassifyUrgency:
    """Test classify_urgency() function."""

    def test_destructive_returns_high(self) -> None:
        """Test 9a: classify_urgency('delete_issue') -> 'high'."""
        assert classify_urgency("delete_issue") == "high"

    def test_content_creation_returns_medium(self) -> None:
        """Test 9b: classify_urgency('create_issue') -> 'medium'."""
        assert classify_urgency("create_issue") == "medium"

    def test_other_returns_low(self) -> None:
        """Test 9c: classify_urgency('ghost_text') -> 'low'."""
        assert classify_urgency("ghost_text") == "low"


# ---------------------------------------------------------------------------
# TestBuildAffectedEntities
# ---------------------------------------------------------------------------


class TestBuildAffectedEntities:
    """Test build_affected_entities() function."""

    def test_issue_id_input(self) -> None:
        """Test 10a: build_affected_entities with issue_id."""
        entities = build_affected_entities("update_issue", {"issue_id": "abc-123"})
        assert len(entities) == 1
        assert entities[0]["type"] == "issue"
        assert entities[0]["id"] == "abc-123"

    def test_note_id_input(self) -> None:
        """Test 10b: build_affected_entities with note_id."""
        entities = build_affected_entities("update_note", {"note_id": "note-1"})
        assert len(entities) == 1
        assert entities[0]["type"] == "note"

    def test_pr_number_input(self) -> None:
        """Test 10c: build_affected_entities with pr_number."""
        entities = build_affected_entities("merge_pr", {"pr_number": 42})
        assert len(entities) == 1
        assert entities[0]["name"] == "PR #42"


# ---------------------------------------------------------------------------
# TestBuildApprovalSseEvent
# ---------------------------------------------------------------------------


class TestBuildApprovalSseEvent:
    """Test build_approval_sse_event() function."""

    def test_sse_event_format(self) -> None:
        """Test 11: build_approval_sse_event produces valid SSE with event: approval_request prefix."""
        with patch("pilot_space.ai.sdk.hooks.PermissionCheckHook") as mock_hook:
            mock_hook.TOOL_ACTION_MAPPING = {"create_issue_in_db": "create_issue"}
            event = build_approval_sse_event(
                approval_id=uuid4(),
                tool_name="create_issue_in_db",
                tool_input={"name": "Test"},
                reason="Needs approval",
            )

        assert event.startswith("event: approval_request\n")
        assert '"actionType": "create_issue"' in event
        assert '"urgency": "medium"' in event
        assert '"requestId"' in event
        assert '"expiresAt"' in event


# ---------------------------------------------------------------------------
# TestApprovalActionExecutor (migrated)
# ---------------------------------------------------------------------------


class TestApprovalActionExecutorMigrated:
    """Verify ApprovalActionExecutor is available from approval_bus module."""

    def test_executor_class_exists(self) -> None:
        """ApprovalActionExecutor is importable from approval_bus."""
        assert ApprovalActionExecutor is not None
        assert hasattr(ApprovalActionExecutor, "execute")
