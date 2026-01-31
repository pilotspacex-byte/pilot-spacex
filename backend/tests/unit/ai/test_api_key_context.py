"""
Unit tests for workspace context management.

Tests verify that request-scoped workspace context is properly isolated
between concurrent async tasks using contextvars.
"""

import asyncio
from uuid import uuid4

import pytest

from pilot_space.ai.context import (
    clear_context,
    get_user_id,
    get_workspace_id,
    set_workspace_context,
)


class TestWorkspaceContext:
    """Test suite for workspace context management."""

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
        set_workspace_context(uuid4(), uuid4())

        clear_context()

        assert get_workspace_id() is None
        assert get_user_id() is None

    @pytest.mark.asyncio
    async def test_context_isolation_between_tasks(self) -> None:
        """Test that context variables are isolated between async tasks."""
        ws_a = uuid4()
        ws_b = uuid4()

        async def task_a() -> str | None:
            """Task A with its own context."""
            set_workspace_context(ws_a, uuid4())
            await asyncio.sleep(0.01)
            return str(get_workspace_id())

        async def task_b() -> str | None:
            """Task B with its own context."""
            set_workspace_context(ws_b, uuid4())
            await asyncio.sleep(0.01)
            return str(get_workspace_id())

        result_a, result_b = await asyncio.gather(task_a(), task_b())

        assert result_a == str(ws_a)
        assert result_b == str(ws_b)
