"""
Unit tests for thread-safe API key context management.

Tests verify that concurrent requests from different workspaces do not
experience race conditions when setting os.environ["ANTHROPIC_API_KEY"].
"""

import asyncio
import os
from uuid import uuid4

import pytest

from pilot_space.ai.context import (
    clear_context,
    get_api_key,
    get_api_key_lock,
    get_user_id,
    get_workspace_id,
    set_api_key,
    set_workspace_context,
)


class TestAPIKeyContext:
    """Test suite for API key context management."""

    def test_set_and_get_api_key(self) -> None:
        """Test setting and retrieving API key from context."""
        test_key = "sk-ant-test-123"
        set_api_key(test_key)

        assert get_api_key() == test_key

        clear_context()
        assert get_api_key() is None

    def test_workspace_context(self) -> None:
        """Test setting and retrieving workspace context."""
        workspace_id = uuid4()
        user_id = uuid4()

        set_workspace_context(workspace_id, user_id)

        assert get_workspace_id() == workspace_id
        assert get_user_id() == user_id

        clear_context()
        assert get_workspace_id() is None
        assert get_user_id() is None

    def test_clear_context_clears_all(self) -> None:
        """Test that clear_context clears all context variables."""
        set_api_key("sk-ant-test-123")
        set_workspace_context(uuid4(), uuid4())

        clear_context()

        assert get_api_key() is None
        assert get_workspace_id() is None
        assert get_user_id() is None

    @pytest.mark.asyncio
    async def test_api_key_lock_serializes_access(self) -> None:
        """Test that the API key lock prevents concurrent os.environ access."""
        original_key = os.environ.get("ANTHROPIC_API_KEY")
        execution_order: list[str] = []

        async def mock_sdk_call(workspace_name: str, api_key: str) -> None:
            """Simulate SDK call that reads from os.environ."""
            async with get_api_key_lock():
                # Set environment variable
                os.environ["ANTHROPIC_API_KEY"] = api_key
                execution_order.append(f"{workspace_name}_start")

                # Simulate SDK work (e.g., API call)
                await asyncio.sleep(0.05)

                # Verify key hasn't been overwritten by another concurrent request
                current_key = os.environ.get("ANTHROPIC_API_KEY")
                assert current_key == api_key, (
                    f"Race condition detected! Expected {api_key}, got {current_key}"
                )

                execution_order.append(f"{workspace_name}_end")

                # Restore original key
                if original_key:
                    os.environ["ANTHROPIC_API_KEY"] = original_key
                elif "ANTHROPIC_API_KEY" in os.environ:
                    del os.environ["ANTHROPIC_API_KEY"]

        # Simulate 3 concurrent requests from different workspaces
        await asyncio.gather(
            mock_sdk_call("workspace_a", "sk-ant-workspace-a-key"),
            mock_sdk_call("workspace_b", "sk-ant-workspace-b-key"),
            mock_sdk_call("workspace_c", "sk-ant-workspace-c-key"),
        )

        # Verify execution was serialized (no interleaving)
        # Each workspace should complete fully before the next starts
        for i in range(0, len(execution_order), 2):
            workspace_name = execution_order[i].replace("_start", "")
            assert execution_order[i] == f"{workspace_name}_start"
            assert execution_order[i + 1] == f"{workspace_name}_end"

        # Verify we had 3 workspaces complete
        assert len(execution_order) == 6

    @pytest.mark.asyncio
    async def test_context_isolation_between_tasks(self) -> None:
        """Test that context variables are isolated between async tasks."""

        async def task_a() -> tuple[str | None, str | None]:
            """Task A with its own context."""
            set_api_key("sk-ant-task-a")
            set_workspace_context(uuid4(), uuid4())
            await asyncio.sleep(0.01)  # Yield control
            return get_api_key(), str(get_workspace_id())

        async def task_b() -> tuple[str | None, str | None]:
            """Task B with its own context."""
            set_api_key("sk-ant-task-b")
            set_workspace_context(uuid4(), uuid4())
            await asyncio.sleep(0.01)  # Yield control
            return get_api_key(), str(get_workspace_id())

        # Run tasks concurrently
        result_a, result_b = await asyncio.gather(task_a(), task_b())

        # Verify each task maintained its own context
        assert result_a[0] == "sk-ant-task-a"
        assert result_b[0] == "sk-ant-task-b"
        assert result_a[1] != result_b[1]  # Different workspace IDs

    @pytest.mark.asyncio
    async def test_lock_prevents_race_condition_without_sleep(self) -> None:
        """Test lock prevents race even with immediate execution."""
        original_key = os.environ.get("ANTHROPIC_API_KEY")
        race_detected = False

        async def fast_sdk_call(workspace_name: str, api_key: str) -> None:
            """Simulate fast SDK call."""
            nonlocal race_detected
            async with get_api_key_lock():
                os.environ["ANTHROPIC_API_KEY"] = api_key
                # Immediately check - no sleep
                current_key = os.environ.get("ANTHROPIC_API_KEY")
                if current_key != api_key:
                    race_detected = True

                # Restore
                if original_key:
                    os.environ["ANTHROPIC_API_KEY"] = original_key
                elif "ANTHROPIC_API_KEY" in os.environ:
                    del os.environ["ANTHROPIC_API_KEY"]

        # Run 10 concurrent fast requests
        tasks = [fast_sdk_call(f"workspace_{i}", f"sk-ant-key-{i}") for i in range(10)]
        await asyncio.gather(*tasks)

        assert not race_detected, "Race condition detected in fast execution"


class TestAPIKeyLockPerformance:
    """Test suite for API key lock performance characteristics."""

    @pytest.mark.asyncio
    async def test_lock_allows_sequential_execution(self) -> None:
        """Test that lock serializes requests but doesn't block unnecessarily."""
        import time

        original_key = os.environ.get("ANTHROPIC_API_KEY")
        start_time = time.monotonic()

        async def sdk_call(delay: float) -> None:
            """Simulate SDK call with delay."""
            async with get_api_key_lock():
                os.environ["ANTHROPIC_API_KEY"] = f"sk-ant-test-{delay}"
                await asyncio.sleep(delay)
                # Restore
                if original_key:
                    os.environ["ANTHROPIC_API_KEY"] = original_key
                elif "ANTHROPIC_API_KEY" in os.environ:
                    del os.environ["ANTHROPIC_API_KEY"]

        # 3 calls with 0.02s each = ~0.06s total if serialized
        await asyncio.gather(
            sdk_call(0.02),
            sdk_call(0.02),
            sdk_call(0.02),
        )

        elapsed = time.monotonic() - start_time

        # Should take at least 0.06s (serialized)
        assert elapsed >= 0.06, "Lock didn't serialize execution"
        # Should not take more than 0.1s (reasonable overhead)
        assert elapsed < 0.1, "Lock added too much overhead"
