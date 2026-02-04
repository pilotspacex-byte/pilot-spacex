"""Tests for RLS context in AI session endpoints.

Verifies that set_rls_context is called before database operations
in ai_sessions and ai_chat routers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.api.v1.routers.ai_sessions import list_sessions, resume_session

TEST_USER_ID = UUID("77a6813e-0aa3-400c-8d4e-540b6ed2187a")


@pytest.mark.asyncio
async def test_list_sessions_sets_rls_context() -> None:
    """list_sessions should call set_rls_context before querying."""
    mock_db = AsyncMock()
    mock_session_manager = MagicMock()
    user_id = TEST_USER_ID

    with (
        patch(
            "pilot_space.api.v1.routers.ai_sessions.set_rls_context",
            new_callable=AsyncMock,
        ) as mock_rls,
        patch(
            "pilot_space.ai.sdk.session_store.SessionStore.list_sessions_for_user",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        result = await list_sessions(
            user_id=user_id,
            db_session=mock_db,
            session_manager=mock_session_manager,
        )

        mock_rls.assert_called_once_with(mock_db, user_id)
        assert result.total == 0


@pytest.mark.asyncio
async def test_resume_session_sets_rls_context() -> None:
    """resume_session should call set_rls_context before loading."""
    mock_db = AsyncMock()
    mock_session_manager = MagicMock()
    user_id = TEST_USER_ID
    session_id = uuid4()

    mock_session = MagicMock()
    mock_session.user_id = user_id
    mock_session.messages = []
    mock_session.context = {}
    mock_session.turn_count = 0
    mock_session.id = session_id

    with (
        patch(
            "pilot_space.api.v1.routers.ai_sessions.set_rls_context",
            new_callable=AsyncMock,
        ) as mock_rls,
        patch(
            "pilot_space.ai.sdk.session_store.SessionStore.load_from_db",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
    ):
        result = await resume_session(
            session_id=session_id,
            user_id=user_id,
            db_session=mock_db,
            session_manager=mock_session_manager,
        )

        mock_rls.assert_called_once_with(mock_db, user_id)
        assert result.session_id == session_id
