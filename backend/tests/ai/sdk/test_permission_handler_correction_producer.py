"""Phase 70 Wave 2 — PROD-02 user_correction producer tests.

Contract: when the workspace policy DENIES a tool call (or a user
rejects an approval request), ``PermissionHandler`` MUST enqueue a
``user_correction`` memory payload via the fire-and-forget producer
helper. When the opt-out flag is ``False``, the enqueue MUST be
dropped silently and the ``PermissionDeniedError`` MUST still raise.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.memory.producers import user_correction_producer
from pilot_space.ai.sdk.permission_handler import PermissionHandler
from pilot_space.ai.telemetry import memory_metrics
from pilot_space.application.services.permissions.exceptions import (
    PermissionDeniedError,
)
from pilot_space.domain.permissions.tool_permission_mode import ToolPermissionMode


def _make_handler(
    *,
    queue_client,
    enabled: bool = True,
    permission_mode: ToolPermissionMode | None = ToolPermissionMode.DENY,
) -> PermissionHandler:
    approval_service = MagicMock()
    approval_service.get_request = AsyncMock(return_value=None)
    approval_service.resolve = AsyncMock()

    permission_service = MagicMock()
    permission_service.resolve = AsyncMock(return_value=permission_mode)

    return PermissionHandler(
        approval_service=approval_service,
        permission_service=permission_service,
        queue_client=queue_client,
        user_correction_enabled=enabled,
    )


@pytest.fixture(autouse=True)
def _reset_counters() -> None:
    memory_metrics.reset_producer_counters()


async def test_deny_enqueues_user_correction_payload() -> None:
    queue_client = MagicMock()
    queue_client.enqueue = AsyncMock()
    handler = _make_handler(queue_client=queue_client)

    workspace_id = uuid4()
    user_id = uuid4()

    with pytest.raises(PermissionDeniedError):
        await handler.check_permission(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="pilot",
            action_name="delete_issue",
            description="",
            proposed_changes={},
        )

    assert queue_client.enqueue.await_count == 1
    _queue_name, payload = queue_client.enqueue.await_args.args
    assert payload["memory_type"] == "user_correction"
    assert payload["subtype"] == "deny"
    assert payload["workspace_id"] == str(workspace_id)
    assert payload["actor_user_id"] == str(user_id)
    assert payload["tool_name"] == "delete_issue"
    assert "reason" in payload

    snapshot = memory_metrics.get_producer_counters()
    assert snapshot["enqueued"].get("user_correction") == 1


async def test_opt_out_flag_off_drops_enqueue() -> None:
    queue_client = MagicMock()
    queue_client.enqueue = AsyncMock()
    handler = _make_handler(queue_client=queue_client, enabled=False)

    with pytest.raises(PermissionDeniedError):
        await handler.check_permission(
            workspace_id=uuid4(),
            user_id=uuid4(),
            agent_name="pilot",
            action_name="delete_issue",
            description="",
            proposed_changes={},
        )

    assert queue_client.enqueue.await_count == 0
    snapshot = memory_metrics.get_producer_counters()
    assert snapshot["dropped"].get("user_correction::opt_out") == 1


async def test_enqueue_failure_is_swallowed_and_raise_propagates() -> None:
    queue_client = MagicMock()
    queue_client.enqueue = AsyncMock(side_effect=RuntimeError("kaboom"))
    handler = _make_handler(queue_client=queue_client)

    with pytest.raises(PermissionDeniedError):
        await handler.check_permission(
            workspace_id=uuid4(),
            user_id=uuid4(),
            agent_name="pilot",
            action_name="delete_issue",
            description="",
            proposed_changes={},
        )

    snapshot = memory_metrics.get_producer_counters()
    assert snapshot["dropped"].get("user_correction::enqueue_error") == 1


async def test_auto_mode_does_not_enqueue_correction() -> None:
    queue_client = MagicMock()
    queue_client.enqueue = AsyncMock()

    # AUTO mode + auto-execute action → no approval request, no correction.
    approval_service = MagicMock()
    approval_service.create_approval_request = AsyncMock(return_value=uuid4())
    permission_service = MagicMock()
    permission_service.resolve = AsyncMock(return_value=ToolPermissionMode.AUTO)

    handler = PermissionHandler(
        approval_service=approval_service,
        permission_service=permission_service,
        queue_client=queue_client,
    )

    result = await handler.check_permission(
        workspace_id=uuid4(),
        user_id=uuid4(),
        agent_name="pilot",
        action_name="search_issues",  # AUTO_EXECUTE baseline
        description="",
        proposed_changes={},
    )

    assert result.allowed is True
    assert queue_client.enqueue.await_count == 0


async def test_producer_helper_direct_opt_out() -> None:
    """Direct unit test for the producer helper opt-out branch."""
    queue_client = MagicMock()
    queue_client.enqueue = AsyncMock()

    await user_correction_producer.enqueue_user_correction_memory(
        queue_client=queue_client,
        workspace_id=uuid4(),
        actor_user_id=uuid4(),
        session_id="sess",
        subtype="deny",
        tool_name="delete_issue",
        reason="nope",
        referenced_turn_index=None,
        enabled=False,
    )

    assert queue_client.enqueue.await_count == 0
    snapshot = memory_metrics.get_producer_counters()
    assert snapshot["dropped"].get("user_correction::opt_out") == 1
