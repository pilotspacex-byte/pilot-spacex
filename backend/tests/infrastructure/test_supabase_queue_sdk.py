"""Tests for SupabaseQueueClient SDK migration.

Verifies that the queue client correctly delegates to the supabase-py
SDK's postgrest.rpc() API and properly maps SDK exceptions to domain
exceptions.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.infrastructure.queue.supabase_queue import (
    QueueConnectionError,
    QueueMessage,
    QueueOperationError,
    SupabaseQueueClient,
    SupabaseQueueError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sdk_client(
    rpc_data: Any = None,
    rpc_raises: Exception | None = None,
) -> MagicMock:
    """Build a mock AsyncClient with postgrest.rpc().execute() pre-wired.

    Args:
        rpc_data: Value to return from response.data.
        rpc_raises: Exception to raise from execute(), or None for success.
    """
    execute_mock = AsyncMock()

    if rpc_raises is not None:
        execute_mock.side_effect = rpc_raises
    else:
        response = MagicMock()
        response.data = rpc_data
        execute_mock.return_value = response

    rpc_builder = MagicMock()
    rpc_builder.execute = execute_mock

    postgrest = MagicMock()
    postgrest.rpc = MagicMock(return_value=rpc_builder)

    sdk_client = MagicMock()
    sdk_client.postgrest = postgrest

    return sdk_client


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


def test_exception_hierarchy() -> None:
    assert issubclass(QueueConnectionError, SupabaseQueueError)
    assert issubclass(QueueOperationError, SupabaseQueueError)


# ---------------------------------------------------------------------------
# _rpc_call internals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rpc_call_calls_postgrest_rpc_execute() -> None:
    sdk_client = _make_sdk_client(rpc_data=42)
    client = SupabaseQueueClient(client=sdk_client)

    result = await client._rpc_call("pgmq_send", {"queue_name": "test", "msg": {}})

    sdk_client.postgrest.rpc.assert_called_once_with("pgmq_send", {"queue_name": "test", "msg": {}})
    assert result == 42


@pytest.mark.asyncio
async def test_rpc_call_void_response_returns_none() -> None:
    """pgmq_create / pgmq_drop return void → SDK response.data is []."""
    sdk_client = _make_sdk_client(rpc_data=[])  # empty list = void response
    client = SupabaseQueueClient(client=sdk_client)

    result = await client._rpc_call("pgmq_create", {"queue_name": "test"})
    assert result is None


@pytest.mark.asyncio
async def test_rpc_call_none_data_returns_none() -> None:
    """response.data=None also treated as void."""
    sdk_client = _make_sdk_client(rpc_data=None)
    client = SupabaseQueueClient(client=sdk_client)

    result = await client._rpc_call("pgmq_drop", {"queue_name": "test"})
    assert result is None


@pytest.mark.asyncio
async def test_rpc_call_api_error_raises_queue_operation_error() -> None:
    """postgrest.exceptions.APIError → QueueOperationError."""
    from postgrest.exceptions import APIError

    exc = APIError({"message": "function not found", "code": "404"})
    sdk_client = _make_sdk_client(rpc_raises=exc)
    client = SupabaseQueueClient(client=sdk_client)

    with pytest.raises(QueueOperationError):
        await client._rpc_call("pgmq_send", {})


@pytest.mark.asyncio
async def test_rpc_call_connect_error_raises_queue_connection_error() -> None:
    """httpx.ConnectError → QueueConnectionError."""
    import httpx

    exc = httpx.ConnectError("Connection refused")
    sdk_client = _make_sdk_client(rpc_raises=exc)
    client = SupabaseQueueClient(client=sdk_client)

    with pytest.raises(QueueConnectionError):
        await client._rpc_call("pgmq_send", {})


@pytest.mark.asyncio
async def test_rpc_call_httpx_request_error_raises_queue_operation_error() -> None:
    """Other httpx errors → QueueOperationError."""
    import httpx

    exc = httpx.ReadTimeout("Read timeout")
    sdk_client = _make_sdk_client(rpc_raises=exc)
    client = SupabaseQueueClient(client=sdk_client)

    with pytest.raises(QueueOperationError):
        await client._rpc_call("pgmq_read", {})


# ---------------------------------------------------------------------------
# enqueue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enqueue_calls_pgmq_send_with_correct_params() -> None:
    sdk_client = _make_sdk_client(rpc_data=99)  # pgmq_send returns msg id
    client = SupabaseQueueClient(client=sdk_client)

    result = await client.enqueue("my-queue", {"key": "value"}, delay_seconds=5)

    rpc_call = sdk_client.postgrest.rpc.call_args
    assert rpc_call[0][0] == "pgmq_send"
    params = rpc_call[0][1]
    assert params["queue_name"] == "my-queue"
    assert params["delay"] == 5
    assert params["msg"]["key"] == "value"
    assert result == "99"  # str(99)


@pytest.mark.asyncio
async def test_enqueue_returns_generated_id_when_send_returns_none() -> None:
    """When pgmq_send returns void/None, enqueue generates a UUID msg_id."""
    sdk_client = _make_sdk_client(rpc_data=[])  # void response
    client = SupabaseQueueClient(client=sdk_client)

    result = await client.enqueue("q", {"x": 1})
    # Should be a non-empty string (the pre-generated uuid)
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# dequeue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dequeue_calls_pgmq_read_and_returns_queue_messages() -> None:
    raw_messages = [
        {
            "msg_id": 1,
            "read_ct": 1,
            "enqueued_at": "2024-01-01T00:00:00Z",
            "vt": "2024-01-01T00:01:00Z",
            "message": {"task": "run"},
        }
    ]
    sdk_client = _make_sdk_client(rpc_data=raw_messages)
    client = SupabaseQueueClient(client=sdk_client)

    messages = await client.dequeue("work-queue", batch_size=5, visibility_timeout=60)

    rpc_call = sdk_client.postgrest.rpc.call_args
    assert rpc_call[0][0] == "pgmq_read"
    params = rpc_call[0][1]
    assert params["queue_name"] == "work-queue"
    assert params["qty"] == 5
    assert params["vt"] == 60
    assert len(messages) == 1
    assert isinstance(messages[0], QueueMessage)


@pytest.mark.asyncio
async def test_dequeue_empty_queue_returns_empty_list() -> None:
    sdk_client = _make_sdk_client(rpc_data=[])
    client = SupabaseQueueClient(client=sdk_client)

    messages = await client.dequeue("empty-queue")
    assert messages == []


# ---------------------------------------------------------------------------
# ack
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ack_calls_pgmq_delete_and_returns_true() -> None:
    sdk_client = _make_sdk_client(rpc_data=True)
    client = SupabaseQueueClient(client=sdk_client)

    result = await client.ack("q", "42")

    rpc_call = sdk_client.postgrest.rpc.call_args
    assert rpc_call[0][0] == "pgmq_delete"
    assert rpc_call[0][1]["msg_id"] == 42  # isdigit → int conversion
    assert result is True


@pytest.mark.asyncio
async def test_ack_returns_false_when_message_not_found() -> None:
    sdk_client = _make_sdk_client(rpc_data=False)
    client = SupabaseQueueClient(client=sdk_client)

    result = await client.ack("q", "999")
    assert result is False


# ---------------------------------------------------------------------------
# create_queue (void response)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_queue_handles_void_response() -> None:
    """pgmq_create returns void — _rpc_call returns None; create_queue returns True."""
    sdk_client = _make_sdk_client(rpc_data=[])  # void
    client = SupabaseQueueClient(client=sdk_client)

    result = await client.create_queue("new-queue")

    rpc_call = sdk_client.postgrest.rpc.call_args
    assert rpc_call[0][0] == "pgmq_create"
    assert result is True


@pytest.mark.asyncio
async def test_create_queue_returns_false_when_already_exists() -> None:
    """QueueOperationError with 'already exists' → returns False."""
    from postgrest.exceptions import APIError

    exc = APIError({"message": "queue already exists", "code": "409"})
    sdk_client = _make_sdk_client(rpc_raises=exc)
    client = SupabaseQueueClient(client=sdk_client)

    result = await client.create_queue("existing-queue")
    assert result is False


# ---------------------------------------------------------------------------
# delete_queue (void response)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_queue_handles_void_response() -> None:
    """pgmq_drop returns void — create_queue returns True."""
    sdk_client = _make_sdk_client(rpc_data=[])
    client = SupabaseQueueClient(client=sdk_client)

    result = await client.delete_queue("old-queue")

    rpc_call = sdk_client.postgrest.rpc.call_args
    assert rpc_call[0][0] == "pgmq_drop"
    assert result is True


# ---------------------------------------------------------------------------
# purge_queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_queue_returns_count() -> None:
    sdk_client = _make_sdk_client(rpc_data=7)  # pgmq_purge returns integer
    client = SupabaseQueueClient(client=sdk_client)

    count = await client.purge_queue("big-queue")
    assert count == 7


# ---------------------------------------------------------------------------
# Lazy SDK client initialisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lazy_client_init_calls_get_supabase_client() -> None:
    """When no client is provided, _get_client() calls get_supabase_client()."""
    import pilot_space.infrastructure.supabase_client as supabase_client_mod

    sdk_client = _make_sdk_client(rpc_data=[])

    mock_get = AsyncMock(return_value=sdk_client)
    original = supabase_client_mod.get_supabase_client
    try:
        supabase_client_mod.get_supabase_client = mock_get  # type: ignore[assignment]
        client = SupabaseQueueClient()  # no client arg
        await client.create_queue("test")
    finally:
        supabase_client_mod.get_supabase_client = original  # type: ignore[assignment]

    mock_get.assert_awaited_once()


# ---------------------------------------------------------------------------
# nack
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nack_requeue_calls_pgmq_set_vt() -> None:
    """nack(requeue=True) should reschedule visibility via pgmq_set_vt."""
    # pgmq_set_vt returns the updated message record (list of dicts)
    sdk_client = _make_sdk_client(rpc_data=[{"msg_id": 5}])
    client = SupabaseQueueClient(client=sdk_client)

    result = await client.nack("q", "5", requeue=True, delay_seconds=30)

    rpc_call = sdk_client.postgrest.rpc.call_args
    assert rpc_call[0][0] == "pgmq_set_vt"
    assert rpc_call[0][1]["msg_id"] == 5
    assert rpc_call[0][1]["vt"] == 30
    assert result is True


@pytest.mark.asyncio
async def test_nack_no_requeue_calls_pgmq_delete() -> None:
    """nack(requeue=False) should delete the message."""
    sdk_client = _make_sdk_client(rpc_data=True)
    client = SupabaseQueueClient(client=sdk_client)

    result = await client.nack("q", "7", requeue=False)

    rpc_call = sdk_client.postgrest.rpc.call_args
    assert rpc_call[0][0] == "pgmq_delete"
    assert rpc_call[0][1]["msg_id"] == 7
    assert result is True


@pytest.mark.asyncio
async def test_nack_default_delay_is_zero() -> None:
    """nack(requeue=True) defaults delay_seconds to 0."""
    sdk_client = _make_sdk_client(rpc_data=[{"msg_id": 1}])
    client = SupabaseQueueClient(client=sdk_client)

    await client.nack("q", "1", requeue=True)

    rpc_call = sdk_client.postgrest.rpc.call_args
    assert rpc_call[0][1]["vt"] == 0


# ---------------------------------------------------------------------------
# move_to_dead_letter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_move_to_dead_letter_enqueues_before_delete() -> None:
    """DLQ enqueue must happen before source queue delete (no message loss)."""
    call_order: list[str] = []

    # Track call order via side effects
    async def track_execute():
        response = MagicMock()
        response.data = 42  # pgmq_send returns msg id
        return response

    rpc_builder = MagicMock()
    rpc_builder.execute = AsyncMock(side_effect=track_execute)

    postgrest = MagicMock()

    def track_rpc(fn, params):
        call_order.append(fn)
        return rpc_builder

    postgrest.rpc = MagicMock(side_effect=track_rpc)

    sdk_client = MagicMock()
    sdk_client.postgrest = postgrest

    client = SupabaseQueueClient(client=sdk_client)

    await client.move_to_dead_letter("source-q", "10", error="failed")

    # pgmq_send (DLQ enqueue) must come before pgmq_delete (source delete)
    assert call_order[0] == "pgmq_send", f"Expected pgmq_send first, got {call_order}"
    assert call_order[-1] == "pgmq_delete", f"Expected pgmq_delete last, got {call_order}"


# ---------------------------------------------------------------------------
# RPC allowlist enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rpc_call_disallowed_function_raises_value_error() -> None:
    """Calling a function not in _ALLOWED_RPC_FUNCTIONS must raise ValueError."""
    sdk_client = _make_sdk_client(rpc_data=None)
    client = SupabaseQueueClient(client=sdk_client)

    with pytest.raises(ValueError, match="Disallowed RPC function"):
        await client._rpc_call("pg_sleep", {"seconds": 10})


def test_allowed_rpc_functions_does_not_contain_archive() -> None:
    """pgmq_archive was replaced by pgmq_set_vt — verify it's removed."""
    assert "pgmq_archive" not in SupabaseQueueClient._ALLOWED_RPC_FUNCTIONS


def test_allowed_rpc_functions_contains_set_vt() -> None:
    """pgmq_set_vt must be in the allowlist for nack(requeue=True)."""
    assert "pgmq_set_vt" in SupabaseQueueClient._ALLOWED_RPC_FUNCTIONS
